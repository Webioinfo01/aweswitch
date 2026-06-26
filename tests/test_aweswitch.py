import json
import os
import stat
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

from click.testing import CliRunner

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aweswitch import cli as aweswitch


class AweSwitchTests(unittest.TestCase):
    def assert_settings_file_secure(self, path):
        if os.name == "nt":
            return
        self.assertEqual(stat.S_IMODE(os.stat(path).st_mode), 0o600)

    def test_init_creates_example_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"

            aweswitch.init_config(path)

            data = json.loads(path.read_text())
            self.assertIn("profiles", data)
            self.assertIn("claude", data["profiles"])
            self.assertIn("cc-glm", data["profiles"]["claude"])
            self.assertIn("codex", data["profiles"])
            self.assertIn("cx-openai", data["profiles"]["codex"])

    def test_package_entry_point_targets_cli_main(self):
        pyproject_path = Path(__file__).resolve().parents[1] / "pyproject.toml"

        data = pyproject_path.read_text()

        self.assertRegex(data, r'version = "\d+\.\d+\.\d+"')
        self.assertIn('aweswitch = "aweswitch.cli:main"', data)
        self.assertIn('dependencies = ["click>=8.1"]', data)

    def test_main_help_uses_click_command_layout(self):
        result = CliRunner().invoke(aweswitch.cli, ["-h"])

        self.assertEqual(result.exit_code, 0)
        self.assertIn("Usage: aweswitch [OPTIONS] COMMAND [ARGS]...", result.output)
        self.assertIn("Agent profile switcher for launching isolated runtime configs.", result.output)
        self.assertIn("-v, --version", result.output)
        self.assertIn("list", result.output)
        self.assertIn("config", result.output)

    def test_version_option(self):
        import aweswitch as pkg
        expected_version = pkg.__version__

        result = CliRunner().invoke(aweswitch.cli, ["-v"])

        self.assertEqual(result.exit_code, 0)
        self.assertIn(expected_version, result.output)

    def test_config_help_uses_click_command_layout(self):
        result = CliRunner().invoke(aweswitch.cli, ["config", "-h"])

        self.assertEqual(result.exit_code, 0)
        self.assertIn("Usage: aweswitch config [OPTIONS] COMMAND [ARGS]...", result.output)
        self.assertIn("Manage aweswitch config.", result.output)
        self.assertIn("path", result.output)
        self.assertIn("show", result.output)
        self.assertIn("edit", result.output)
        self.assertIn("init", result.output)

    def test_save_profile_adds_new_claude_profile(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            aweswitch.init_config(path)

            aweswitch.save_profile(path, "my-profile", {
                "ANTHROPIC_BASE_URL": "https://example.com",
                "ANTHROPIC_AUTH_TOKEN": "${MY_TOKEN}",
                "ANTHROPIC_MODEL": "test-model",
            }, provider="claude")

            data = json.loads(path.read_text())
            profile = data["profiles"]["claude"]["my-profile"]
            self.assertEqual(profile["env"]["ANTHROPIC_BASE_URL"], "https://example.com")
            self.assertEqual(profile["env"]["ANTHROPIC_AUTH_TOKEN"], "${MY_TOKEN}")
            self.assertEqual(profile["env"]["ANTHROPIC_MODEL"], "test-model")

    def test_save_profile_adds_new_codex_profile(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            aweswitch.init_config(path)

            aweswitch.save_profile(path, "cx-test", {
                "OPENAI_BASE_URL": "https://api.example.com/v1",
                "OPENAI_API_KEY": "${MY_KEY}",
            }, provider="codex")

            data = json.loads(path.read_text())
            profile = data["profiles"]["codex"]["cx-test"]
            self.assertEqual(profile["env"]["OPENAI_BASE_URL"], "https://api.example.com/v1")
            self.assertEqual(profile["env"]["OPENAI_API_KEY"], "${MY_KEY}")

    def test_save_profile_skips_empty_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            aweswitch.init_config(path)

            aweswitch.save_profile(path, "minimal", {
                "ANTHROPIC_BASE_URL": "https://example.com",
                "ANTHROPIC_AUTH_TOKEN": "${T}",
                "ANTHROPIC_MODEL": "m",
                "ANTHROPIC_DEFAULT_HAIKU_MODEL": "",
                "ANTHROPIC_DEFAULT_SONNET_MODEL": "",
            }, provider="claude")

            data = json.loads(path.read_text())
            env = data["profiles"]["claude"]["minimal"]["env"]
            self.assertNotIn("ANTHROPIC_DEFAULT_HAIKU_MODEL", env)
            self.assertNotIn("ANTHROPIC_DEFAULT_SONNET_MODEL", env)

    def test_save_profile_rejects_duplicate(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            aweswitch.init_config(path)

            aweswitch.save_profile(path, "dup", {
                "ANTHROPIC_BASE_URL": "https://example.com",
                "ANTHROPIC_AUTH_TOKEN": "${T}",
                "ANTHROPIC_MODEL": "m",
            }, provider="claude")
            with self.assertRaisesRegex(SystemExit, "already exists"):
                aweswitch.save_profile(path, "dup", {
                    "ANTHROPIC_BASE_URL": "https://other.com",
                    "ANTHROPIC_AUTH_TOKEN": "${T}",
                    "ANTHROPIC_MODEL": "m",
                }, provider="claude")

    def test_add_command_creates_claude_profile(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            aweswitch.init_config(path)

            result = CliRunner().invoke(aweswitch.cli, [
                "add",
            ], input="claude\ntest-profile\nhttps://example.com\nMY_TOKEN\ntest-model\n\n\n",
                env={"AWESWITCH_CONFIG": str(path)})

            self.assertEqual(result.exit_code, 0, result.output)
            self.assertIn("Profile 'test-profile' added.", result.output)

            data = json.loads(path.read_text())
            profile = data["profiles"]["claude"]["test-profile"]
            self.assertEqual(profile["env"]["ANTHROPIC_BASE_URL"], "https://example.com")
            self.assertEqual(profile["env"]["ANTHROPIC_AUTH_TOKEN"], "${MY_TOKEN}")
            self.assertEqual(profile["env"]["ANTHROPIC_MODEL"], "test-model")
            self.assertNotIn("ANTHROPIC_DEFAULT_HAIKU_MODEL", profile["env"])
            self.assertNotIn("ANTHROPIC_DEFAULT_SONNET_MODEL", profile["env"])

    def test_add_command_with_optional_models(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            aweswitch.init_config(path)

            result = CliRunner().invoke(aweswitch.cli, [
                "add",
            ], input="claude\nfull-profile\nhttps://example.com\nMY_TOKEN\nmy-model\nhaiku-m\nsonnet-m\n",
                env={"AWESWITCH_CONFIG": str(path)})

            self.assertEqual(result.exit_code, 0, result.output)

            data = json.loads(path.read_text())
            env = data["profiles"]["claude"]["full-profile"]["env"]
            self.assertEqual(env["ANTHROPIC_DEFAULT_HAIKU_MODEL"], "haiku-m")
            self.assertEqual(env["ANTHROPIC_DEFAULT_SONNET_MODEL"], "sonnet-m")

    def test_add_command_creates_codex_profile(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            aweswitch.init_config(path)

            result = CliRunner().invoke(aweswitch.cli, [
                "add",
            ], input="codex\ncx-test\nhttps://api.example.com/v1\nMY_KEY\n",
                env={"AWESWITCH_CONFIG": str(path)})

            self.assertEqual(result.exit_code, 0, result.output)
            self.assertIn("Profile 'cx-test' added.", result.output)

            data = json.loads(path.read_text())
            profile = data["profiles"]["codex"]["cx-test"]
            self.assertEqual(profile["env"]["OPENAI_BASE_URL"], "https://api.example.com/v1")
            self.assertEqual(profile["env"]["OPENAI_API_KEY"], "${MY_KEY}")

    def test_prepare_claude_uses_provider_command_and_env_overrides(self):
        config = {
            "profiles": {
                "claude": {
                    "cc-glm": {
                        "env": {
                            "ANTHROPIC_BASE_URL": "${GLM_BASE}",
                            "ANTHROPIC_AUTH_TOKEN": "${GLM_TOKEN}",
                            "ANTHROPIC_MODEL": "glm-5.1",
                        },
                    }
                }
            }
        }
        base_env = {"PATH": "/bin", "GLM_BASE": "https://example.test", "GLM_TOKEN": "secret"}

        argv, env, _ = aweswitch.prepare_run(config, "cc-glm", ["--verbose"], base_env)

        self.assertEqual(argv[0], "claude")
        self.assertEqual(argv[1], "--settings")
        settings_path = argv[2]
        self.assertTrue(os.path.isfile(settings_path))
        self.assert_settings_file_secure(settings_path)
        self.assertEqual(json.loads(Path(settings_path).read_text()), {
            "env": {
                "ANTHROPIC_BASE_URL": "https://example.test",
                "ANTHROPIC_AUTH_TOKEN": "secret",
                "ANTHROPIC_MODEL": "glm-5.1",
                "ANTHROPIC_DEFAULT_OPUS_MODEL": "glm-5.1",
                "ANTHROPIC_DEFAULT_OPUS_MODEL_NAME": "glm-5.1",
                "ANTHROPIC_DEFAULT_HAIKU_MODEL_NAME": "Not set",
                "ANTHROPIC_DEFAULT_SONNET_MODEL_NAME": "Not set",
            }
        })
        self.assertEqual(argv[3:], ["--verbose"])
        self.assertNotIn("ANTHROPIC_MODEL", env)
        self.assertNotIn("ANTHROPIC_BASE_URL", env)
        self.assertNotIn("ANTHROPIC_AUTH_TOKEN", env)
        self.assertEqual(base_env.get("ANTHROPIC_MODEL"), None)

    def test_prepare_claude_can_expand_from_claude_settings_env(self):
        config = {
            "profiles": {
                "claude": {
                    "cc-glm": {
                        "env": {
                            "ANTHROPIC_BASE_URL": "${ANTHROPIC_BASE_URL}",
                            "ANTHROPIC_AUTH_TOKEN": "${ANTHROPIC_AUTH_TOKEN}",
                            "ANTHROPIC_MODEL": "glm-5.1",
                        },
                    }
                }
            }
        }
        claude_settings_env = {
            "ANTHROPIC_BASE_URL": "https://example.test",
            "ANTHROPIC_AUTH_TOKEN": "secret",
        }

        argv, env, _ = aweswitch.prepare_run(config, "cc-glm", [], {}, claude_settings_env)

        self.assertEqual(argv[0], "claude")
        self.assertEqual(argv[1], "--settings")
        settings_path = argv[2]
        self.assertTrue(os.path.isfile(settings_path))
        self.assert_settings_file_secure(settings_path)
        self.assertEqual(json.loads(Path(settings_path).read_text()), {
            "env": {
                "ANTHROPIC_BASE_URL": "https://example.test",
                "ANTHROPIC_AUTH_TOKEN": "secret",
                "ANTHROPIC_MODEL": "glm-5.1",
                "ANTHROPIC_DEFAULT_OPUS_MODEL": "glm-5.1",
                "ANTHROPIC_DEFAULT_OPUS_MODEL_NAME": "glm-5.1",
                "ANTHROPIC_DEFAULT_HAIKU_MODEL_NAME": "Not set",
                "ANTHROPIC_DEFAULT_SONNET_MODEL_NAME": "Not set",
            }
        })
        self.assertEqual(env, {})

    def test_prepare_claude_only_uses_settings_env_for_model(self):
        config = {
            "profiles": {
                "claude": {
                    "cc-glm": {
                        "env": {
                            "ANTHROPIC_BASE_URL": "https://example.test",
                            "ANTHROPIC_AUTH_TOKEN": "secret",
                            "ANTHROPIC_MODEL": "glm-5.1",
                        },
                    }
                }
            }
        }
        base_env = {"ANTHROPIC_MODEL": "old-model"}

        argv, env, _ = aweswitch.prepare_run(config, "cc-glm", [], base_env)

        self.assertEqual(env["ANTHROPIC_MODEL"], "old-model")
        self.assertEqual(argv[0], "claude")
        self.assertEqual(argv[1], "--settings")
        settings_path = argv[2]
        self.assertTrue(os.path.isfile(settings_path))
        self.assert_settings_file_secure(settings_path)
        self.assertEqual(json.loads(Path(settings_path).read_text()), {
            "env": {
                "ANTHROPIC_BASE_URL": "https://example.test",
                "ANTHROPIC_AUTH_TOKEN": "secret",
                "ANTHROPIC_MODEL": "glm-5.1",
                "ANTHROPIC_DEFAULT_OPUS_MODEL": "glm-5.1",
                "ANTHROPIC_DEFAULT_OPUS_MODEL_NAME": "glm-5.1",
                "ANTHROPIC_DEFAULT_HAIKU_MODEL_NAME": "Not set",
                "ANTHROPIC_DEFAULT_SONNET_MODEL_NAME": "Not set",
            }
        })

    def test_prepare_claude_ignores_top_level_model(self):
        config = {
            "profiles": {
                "claude": {
                    "cc-glm": {
                        "model": "ignored-model",
                        "env": {
                            "ANTHROPIC_BASE_URL": "https://example.test",
                            "ANTHROPIC_AUTH_TOKEN": "secret",
                            "ANTHROPIC_MODEL": "glm-5.1",
                        },
                    }
                }
            }
        }

        argv, env, _ = aweswitch.prepare_run(config, "cc-glm", [], {})

        self.assertEqual(env, {})
        self.assertNotIn("--model", argv)
        self.assertNotIn("ignored-model", argv)

    def test_prepare_codex_uses_config_overrides_and_env(self):
        config = {
            "profiles": {
                "codex": {
                    "cx-test": {
                        "env": {
                            "OPENAI_BASE_URL": "${CODEX_BASE}",
                            "OPENAI_API_KEY": "${CODEX_KEY}",
                        },
                    }
                }
            }
        }
        base_env = {"PATH": "/bin", "CODEX_BASE": "https://provider.test/v1", "CODEX_KEY": "sk-test"}

        argv, env, _ = aweswitch.prepare_run(config, "cx-test", ["--verbose"], base_env)

        self.assertEqual(argv[0], "codex")
        self.assertIn("-c", argv)
        # Verify -c flags contain the expected overrides
        c_args = []
        i = 1
        while i < len(argv):
            if argv[i] == "-c" and i + 1 < len(argv):
                c_args.append(argv[i + 1])
                i += 2
            else:
                break
        self.assertIn('model_provider="custom"', c_args)
        self.assertIn('model_providers.custom.base_url="https://provider.test/v1"', c_args)
        self.assertIn('model_providers.custom.wire_api="responses"', c_args)
        self.assertIn('disable_response_storage=true', c_args)
        # API key injected via env, not argv
        self.assertEqual(env["OPENAI_API_KEY"], "sk-test")
        self.assertNotIn("OPENAI_API_KEY", " ".join(argv))
        # User args passed through
        self.assertIn("--verbose", argv)

    def test_prepare_codex_rejects_missing_base_url(self):
        config = {
            "profiles": {
                "codex": {
                    "cx-bad": {
                        "env": {
                            "OPENAI_API_KEY": "${KEY}",
                        },
                    }
                }
            }
        }

        with self.assertRaisesRegex(SystemExit, "OPENAI_BASE_URL is required"):
            aweswitch.prepare_run(config, "cx-bad", [], {"KEY": "sk-test"})

    def test_prepare_codex_rejects_missing_api_key(self):
        config = {
            "profiles": {
                "codex": {
                    "cx-bad": {
                        "env": {
                            "OPENAI_BASE_URL": "https://example.com/v1",
                        },
                    }
                }
            }
        }

        with self.assertRaisesRegex(SystemExit, "OPENAI_API_KEY is required"):
            aweswitch.prepare_run(config, "cx-bad", [], {})

    def test_prepare_rejects_unknown_provider(self):
        config = {
            "profiles": {
                "unknown": {
                    "test": {"env": {}},
                }
            }
        }

        with self.assertRaisesRegex(SystemExit, "unsupported provider"):
            aweswitch.prepare_run(config, "test", [], {})

    def test_profile_model_label_uses_anthropic_model_for_claude(self):
        self.assertEqual(
            aweswitch.profile_model_label("claude", {"env": {"ANTHROPIC_MODEL": "glm-5.1"}}),
            "glm-5.1",
        )

    def test_profile_model_label_uses_base_url_for_codex(self):
        self.assertEqual(
            aweswitch.profile_model_label("codex", {"env": {"OPENAI_BASE_URL": "https://api.test/v1"}}),
            "https://api.test/v1",
        )

    def test_profile_for_errors_on_duplicate_profile_names(self):
        config = {
            "profiles": {
                "claude": {"default": {"env": {}}},
                "codex": {"default": {"env": {}}},
            }
        }

        with self.assertRaisesRegex(SystemExit, "ambiguous profile"):
            aweswitch.profile_for(config, "default")

    def test_redact_hides_secret_values(self):
        data = {
            "profiles": {
                "x": {
                    "env": {
                        "ANTHROPIC_AUTH_TOKEN": "secret",
                        "ANTHROPIC_BASE_URL": "https://example.test",
                    }
                }
            }
        }

        redacted = aweswitch.redact(data)

        self.assertEqual(redacted["profiles"]["x"]["env"]["ANTHROPIC_AUTH_TOKEN"], "<redacted>")
        self.assertEqual(redacted["profiles"]["x"]["env"]["ANTHROPIC_BASE_URL"], "https://example.test")

    def test_redact_hides_codex_api_key(self):
        data = {
            "profiles": {
                "x": {
                    "env": {
                        "OPENAI_API_KEY": "sk-secret",
                        "OPENAI_BASE_URL": "https://example.test",
                    }
                }
            }
        }

        redacted = aweswitch.redact(data)

        self.assertEqual(redacted["profiles"]["x"]["env"]["OPENAI_API_KEY"], "<redacted>")
        self.assertEqual(redacted["profiles"]["x"]["env"]["OPENAI_BASE_URL"], "https://example.test")

    def test_expand_env_errors_on_missing_variable(self):
        with self.assertRaisesRegex(SystemExit, "required environment variable not set"):
            aweswitch.expand_value("${MISSING_ENV}", {})

    def test_editor_argv_splits_editor_with_flags(self):
        argv = aweswitch.editor_argv("code -w", Path("/tmp/config.json"))

        self.assertEqual(argv, ["code", "-w", str(Path("/tmp/config.json"))])

    def test_exec_agent_reports_missing_command(self):
        with self.assertRaisesRegex(SystemExit, "command not found"):
            aweswitch.exec_agent(["/tmp/aweswitch-command-that-does-not-exist"], {})

    def test_generate_codex_config_produces_valid_toml(self):
        config = aweswitch.generate_codex_config("AiHubMix", "https://aihubmix.com/v1")

        self.assertIn('model_provider = "aihubmix"', config)
        self.assertIn('base_url = "https://aihubmix.com/v1"', config)
        self.assertIn('wire_api = "responses"', config)
        self.assertIn('requires_openai_auth = true', config)
        self.assertIn("[model_providers.aihubmix]", config)


    # --- opencode profiles ---

    def _make_oc_config(self, models=None,
                        base_url="https://example.com/v1", api_key="sk-test"):
        if models is None:
            models = {"glm-5.1": "GLM-5.1", "glm-5.2": "GLM-5.2"}
        return {
            "profiles": {
                "opencode": {
                    "oc-test": {
                        "env": {
                            "OPENCODE_BASE_URL": base_url,
                            "OPENCODE_API_KEY": api_key,
                            "OPENCODE_MODEL": models,
                        }
                    }
                }
            }
        }

    def test_prepare_opencode_uses_model_from_args(self):
        config = self._make_oc_config()

        argv, env, oc_info = aweswitch.prepare_run(config, "oc-test", ["glm-5.1"], {})

        self.assertEqual(argv[0], "opencode")
        self.assertEqual(argv[1:3], ["-m", "oc-test/glm-5.1"])
        self.assertEqual(env, {})
        self.assertEqual(oc_info["provider_name"], "oc-test")
        self.assertEqual(oc_info["model"], "glm-5.1")
        self.assertEqual(oc_info["base_url"], "https://example.com/v1")
        self.assertEqual(oc_info["api_key"], "sk-test")
        self.assertEqual(oc_info["api_key_ref"], "sk-test")  # no ${VAR}, so ref == key

    def test_prepare_opencode_passes_extra_args(self):
        config = self._make_oc_config(models={"mimo-v2.5-pro": "MiMo"})

        argv, env, _ = aweswitch.prepare_run(config, "oc-test",
                                              ["mimo-v2.5-pro", "--mini"], {})

        self.assertEqual(argv[1:3], ["-m", "oc-test/mimo-v2.5-pro"])
        self.assertIn("--mini", argv)
        self.assertNotIn("mimo-v2.5-pro", argv[3:])  # model stripped from extra args

    def test_prepare_opencode_expands_env_refs(self):
        config = self._make_oc_config(api_key="${MY_KEY}")
        base_env = {"MY_KEY": "sk-resolved"}

        argv, env, oc_info = aweswitch.prepare_run(config, "oc-test", ["glm-5.1"], base_env)

        self.assertEqual(oc_info["api_key"], "sk-resolved")
        self.assertEqual(oc_info["api_key_ref"], "{env:MY_KEY}")

    def test_prepare_opencode_defaults_to_first_model(self):
        config = self._make_oc_config()

        argv, env, oc_info = aweswitch.prepare_run(config, "oc-test", [], {})

        self.assertEqual(argv[1:3], ["-m", "oc-test/glm-5.1"])
        self.assertEqual(oc_info["model"], "glm-5.1")

    def test_prepare_opencode_rejects_unknown_model(self):
        config = self._make_oc_config()

        with self.assertRaisesRegex(SystemExit, "unknown model 'glm-9.9'"):
            aweswitch.prepare_run(config, "oc-test", ["glm-9.9"], {})

    def test_prepare_opencode_rejects_missing_base_url(self):
        config = {"profiles": {"opencode": {"oc-bad": {"env": {
            "OPENCODE_API_KEY": "k", "OPENCODE_MODEL": {"m": "M"},
        }}}}}

        with self.assertRaisesRegex(SystemExit, "OPENCODE_BASE_URL is required"):
            aweswitch.prepare_run(config, "oc-bad", ["m"], {})

    def test_prepare_opencode_rejects_missing_api_key(self):
        config = {"profiles": {"opencode": {"oc-bad": {"env": {
            "OPENCODE_BASE_URL": "https://x", "OPENCODE_MODEL": {"m": "M"},
        }}}}}

        with self.assertRaisesRegex(SystemExit, "OPENCODE_API_KEY is required"):
            aweswitch.prepare_run(config, "oc-bad", ["m"], {})

    def test_prepare_opencode_rejects_empty_model(self):
        config = {"profiles": {"opencode": {"oc-bad": {"env": {
            "OPENCODE_BASE_URL": "https://x", "OPENCODE_API_KEY": "k",
            "OPENCODE_MODEL": {},
        }}}}}

        with self.assertRaisesRegex(SystemExit, "OPENCODE_MODEL is required"):
            aweswitch.prepare_run(config, "oc-bad", ["m"], {})

    def test_profile_model_label_shows_available_models_for_opencode(self):
        profile = {"env": {"OPENCODE_MODEL": {"glm-5.1": "GLM-5.1", "glm-5.2": "GLM-5.2"}}}
        label = aweswitch.profile_model_label("opencode", profile)
        self.assertIn("glm-5.1", label)
        self.assertIn("glm-5.2", label)

    def test_init_creates_opencode_profiles(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"

            aweswitch.init_config(path)

            data = json.loads(path.read_text())
            self.assertIn("opencode", data["profiles"])
            self.assertIn("oc-glm", data["profiles"]["opencode"])
            env = data["profiles"]["opencode"]["oc-glm"]["env"]
            self.assertNotIn("OPENCODE_PROVIDER", env)
            self.assertIsInstance(env["OPENCODE_MODEL"], dict)
            self.assertIn("glm-5.1", env["OPENCODE_MODEL"])

    def test_ensure_opencode_provider_creates_new_provider_with_env_ref(self):
        with tempfile.TemporaryDirectory() as tmp:
            oc_path = Path(tmp) / "opencode.json"
            oc_path.write_text(json.dumps({"provider": {}}))

            with unittest.mock.patch("aweswitch.cli.opencode_config_path", return_value=oc_path):
                aweswitch.ensure_opencode_provider("https://new.com/v1", "sk-new",
                                                   "{env:MY_KEY}", "oc-doubao", "doubao-1")

            data = json.loads(oc_path.read_text())
            prov = data["provider"]["oc-doubao"]
            self.assertEqual(prov["options"]["baseURL"], "https://new.com/v1")
            self.assertEqual(prov["options"]["apiKey"], "{env:MY_KEY}")
            self.assertIn("doubao-1", prov["models"])

    def test_ensure_opencode_provider_adds_model_to_existing(self):
        with tempfile.TemporaryDirectory() as tmp:
            oc_path = Path(tmp) / "opencode.json"
            oc_path.write_text(json.dumps({"provider": {
                "oc-glm": {
                    "options": {"baseURL": "https://zhipu.com/v1", "apiKey": "{env:GLM_KEY}"},
                    "models": {"glm-5.1": {"name": "glm-5.1"}},
                }
            }}))

            with unittest.mock.patch("aweswitch.cli.opencode_config_path", return_value=oc_path):
                aweswitch.ensure_opencode_provider("https://zhipu.com/v1", "sk-resolved",
                                                   "{env:GLM_KEY}", "oc-glm", "glm-5.2")

            data = json.loads(oc_path.read_text())
            self.assertIn("glm-5.2", data["provider"]["oc-glm"]["models"])
            self.assertIn("glm-5.1", data["provider"]["oc-glm"]["models"])

    def test_ensure_opencode_provider_skips_if_model_exists(self):
        with tempfile.TemporaryDirectory() as tmp:
            oc_path = Path(tmp) / "opencode.json"
            original = {"provider": {
                "oc-glm": {
                    "options": {"baseURL": "https://zhipu.com/v1", "apiKey": "{env:GLM_KEY}"},
                    "models": {"glm-5.1": {"name": "glm-5.1"}},
                }
            }}
            original_text = json.dumps(original, indent=2) + "\n"
            oc_path.write_text(original_text)

            with unittest.mock.patch("aweswitch.cli.opencode_config_path", return_value=oc_path):
                aweswitch.ensure_opencode_provider("https://zhipu.com/v1", "sk-resolved",
                                                   "{env:GLM_KEY}", "oc-glm", "glm-5.1")

            self.assertEqual(oc_path.read_text(), original_text)

    def test_ensure_opencode_provider_rejects_credential_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            oc_path = Path(tmp) / "opencode.json"
            oc_path.write_text(json.dumps({"provider": {
                "oc-glm": {
                    "options": {"baseURL": "https://old.com/v1", "apiKey": "sk-old"},
                    "models": {},
                }
            }}))

            with unittest.mock.patch("aweswitch.cli.opencode_config_path", return_value=oc_path):
                with self.assertRaisesRegex(SystemExit, "already exists with different credentials"):
                    aweswitch.ensure_opencode_provider("https://new.com/v1", "sk-new",
                                                       "{env:NEW_KEY}", "oc-glm", "glm-5.1")


if __name__ == "__main__":
    unittest.main()
