import json
import os
import stat
import sys
import tempfile
import time
import unittest
import io
import unittest.mock
from pathlib import Path

from click.testing import CliRunner

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aweswitch import cli as aweswitch
from aweswitch import update_check


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
            self.assertIn("accounts", data["profiles"])
            self.assertIn("claude", data["profiles"]["api"])
            self.assertIn("cc-glm", data["profiles"]["api"]["claude"])
            self.assertIn("codex", data["profiles"]["api"])
            self.assertIn("cx-openai", data["profiles"]["api"]["codex"])

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
            profile = data["profiles"]["api"]["claude"]["my-profile"]
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
            profile = data["profiles"]["api"]["codex"]["cx-test"]
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
            env = data["profiles"]["api"]["claude"]["minimal"]["env"]
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

    def test_save_profile_rejects_reserved_command_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            aweswitch.init_config(path)

            with self.assertRaisesRegex(SystemExit, "reserved command name"):
                aweswitch.save_profile(path, "list", {
                    "ANTHROPIC_BASE_URL": "https://example.com",
                    "ANTHROPIC_AUTH_TOKEN": "${T}",
                    "ANTHROPIC_MODEL": "m",
                }, provider="claude")

    def test_save_account_rejects_unsafe_filesystem_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            aweswitch.init_config(path)

            with self.assertRaisesRegex(SystemExit, "single path component"):
                aweswitch.save_account(path, "codex", "../../../escape", {"token": "x"})

            data = json.loads(path.read_text())
            self.assertEqual(data["profiles"]["accounts"], {})

    def test_add_command_creates_claude_profile(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            aweswitch.init_config(path)

            result = CliRunner().invoke(aweswitch.cli, [
                "add",
            ], input="api\nclaude\ntest-profile\nhttps://example.com\nMY_TOKEN\ntest-model\n\n\n",
                env={"AWESWITCH_CONFIG": str(path)})

            self.assertEqual(result.exit_code, 0, result.output)
            self.assertIn("Profile 'test-profile' added.", result.output)

            data = json.loads(path.read_text())
            profile = data["profiles"]["api"]["claude"]["test-profile"]
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
            ], input="api\nclaude\nfull-profile\nhttps://example.com\nMY_TOKEN\nmy-model\nhaiku-m\nsonnet-m\n",
                env={"AWESWITCH_CONFIG": str(path)})

            self.assertEqual(result.exit_code, 0, result.output)

            data = json.loads(path.read_text())
            env = data["profiles"]["api"]["claude"]["full-profile"]["env"]
            self.assertEqual(env["ANTHROPIC_DEFAULT_HAIKU_MODEL"], "haiku-m")
            self.assertEqual(env["ANTHROPIC_DEFAULT_SONNET_MODEL"], "sonnet-m")

    def test_add_command_creates_codex_profile(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            aweswitch.init_config(path)

            result = CliRunner().invoke(aweswitch.cli, [
                "add",
            ], input="api\ncodex\ncx-test\nhttps://api.example.com/v1\nMY_KEY\ngpt-5.2-codex, kimi-k2.7\n",
                env={"AWESWITCH_CONFIG": str(path)})

            self.assertEqual(result.exit_code, 0, result.output)
            self.assertIn("Profile 'cx-test' added.", result.output)

            data = json.loads(path.read_text())
            profile = data["profiles"]["api"]["codex"]["cx-test"]
            self.assertEqual(profile["env"]["OPENAI_BASE_URL"], "https://api.example.com/v1")
            self.assertEqual(profile["env"]["OPENAI_API_KEY"], "${MY_KEY}")
            self.assertEqual(profile["env"]["OPENAI_MODEL"],
                             {"gpt-5.2-codex": "gpt-5.2-codex", "kimi-k2.7": "kimi-k2.7"})

    def test_add_command_codex_model_prompt_optional(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            aweswitch.init_config(path)

            result = CliRunner().invoke(aweswitch.cli, [
                "add",
            ], input="api\ncodex\ncx-test\nhttps://api.example.com/v1\nMY_KEY\n\n",
                env={"AWESWITCH_CONFIG": str(path)})

            self.assertEqual(result.exit_code, 0, result.output)

            data = json.loads(path.read_text())
            profile = data["profiles"]["api"]["codex"]["cx-test"]
            self.assertNotIn("OPENAI_MODEL", profile["env"])

    @unittest.mock.patch("aweswitch.cli.subprocess.run")
    def test_add_command_official_login_runs_login_flow(self, mock_run):
        with tempfile.TemporaryDirectory() as tmp:
            config_file = Path(tmp) / "config.json"
            aweswitch.init_config(config_file)

            def fake_login(argv, env=None):
                cred_path = Path(env["CODEX_HOME"]) / "auth.json"
                cred_path.write_text(json.dumps({"tokens": {"access_token": "fresh"}}))
                return unittest.mock.MagicMock(returncode=0)

            mock_run.side_effect = fake_login

            result = CliRunner().invoke(aweswitch.cli, [
                "add",
            ], input="official\ncodex\ncxo-work\n\n",
                env={"AWESWITCH_CONFIG": str(config_file)})

            self.assertEqual(result.exit_code, 0, result.output)
            data = json.loads(config_file.read_text())
            self.assertEqual(data["profiles"]["accounts"]["codex"]["cxo-work"]["auth"],
                             {"tokens": {"access_token": "fresh"}})

    def test_add_command_official_import_reads_live_credentials(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_file = Path(tmp) / "config.json"
            aweswitch.init_config(config_file)
            live_dir = Path(tmp) / "codex"
            live_dir.mkdir()
            blob = {"tokens": {"access_token": "tok", "refresh_token": "ref"}}
            (live_dir / "auth.json").write_text(json.dumps(blob))

            result = CliRunner().invoke(aweswitch.cli, [
                "add",
            ], input="official\ncodex\ncxo-work\nimport\n",
                env={"AWESWITCH_CONFIG": str(config_file),
                     "CODEX_CONFIG": str(live_dir / "config.toml")})

            self.assertEqual(result.exit_code, 0, result.output)
            data = json.loads(config_file.read_text())
            self.assertEqual(data["profiles"]["accounts"]["codex"]["cxo-work"]["auth"], blob)
            self.assert_settings_file_secure(config_file)

    def test_prepare_claude_uses_provider_command_and_env_overrides(self):
        config = {
            "profiles": {
                "api": {
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
        }
        base_env = {"PATH": "/bin", "GLM_BASE": "https://example.test", "GLM_TOKEN": "secret"}

        argv, env, _, _ = aweswitch.prepare_run(config, "cc-glm", ["--verbose"], base_env)

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
                "ANTHROPIC_DEFAULT_SONNET_MODEL": "glm-5.1",
                "ANTHROPIC_DEFAULT_HAIKU_MODEL": "glm-5.1",
                "ANTHROPIC_DEFAULT_FABLE_MODEL": "glm-5.1",
                "ANTHROPIC_DEFAULT_OPUS_MODEL_NAME": "glm-5.1",
                "ANTHROPIC_DEFAULT_SONNET_MODEL_NAME": "glm-5.1",
                "ANTHROPIC_DEFAULT_HAIKU_MODEL_NAME": "glm-5.1",
                "ANTHROPIC_DEFAULT_FABLE_MODEL_NAME": "glm-5.1",
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
                "api": {
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
        }
        claude_settings_env = {
            "ANTHROPIC_BASE_URL": "https://example.test",
            "ANTHROPIC_AUTH_TOKEN": "secret",
        }

        argv, env, _, _ = aweswitch.prepare_run(config, "cc-glm", [], {}, claude_settings_env)

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
                "ANTHROPIC_DEFAULT_SONNET_MODEL": "glm-5.1",
                "ANTHROPIC_DEFAULT_HAIKU_MODEL": "glm-5.1",
                "ANTHROPIC_DEFAULT_FABLE_MODEL": "glm-5.1",
                "ANTHROPIC_DEFAULT_OPUS_MODEL_NAME": "glm-5.1",
                "ANTHROPIC_DEFAULT_SONNET_MODEL_NAME": "glm-5.1",
                "ANTHROPIC_DEFAULT_HAIKU_MODEL_NAME": "glm-5.1",
                "ANTHROPIC_DEFAULT_FABLE_MODEL_NAME": "glm-5.1",
            }
        })
        self.assertEqual(env, {})

    def test_prepare_claude_only_uses_settings_env_for_model(self):
        config = {
            "profiles": {
                "api": {
                    "claude": {
                        "cc-glm": {
                            "env": {
                                "ANTHROPIC_BASE_URL": "https://example.test",
                                "ANTHROPIC_AUTH_TOKEN": "${SECRET_TOKEN}",
                                "ANTHROPIC_MODEL": "glm-5.1",
                            },
                        }
                    }
                }
            }
        }
        base_env = {"ANTHROPIC_MODEL": "old-model", "SECRET_TOKEN": "secret"}

        argv, env, _, _ = aweswitch.prepare_run(config, "cc-glm", [], base_env)

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
                "ANTHROPIC_DEFAULT_SONNET_MODEL": "glm-5.1",
                "ANTHROPIC_DEFAULT_HAIKU_MODEL": "glm-5.1",
                "ANTHROPIC_DEFAULT_FABLE_MODEL": "glm-5.1",
                "ANTHROPIC_DEFAULT_OPUS_MODEL_NAME": "glm-5.1",
                "ANTHROPIC_DEFAULT_SONNET_MODEL_NAME": "glm-5.1",
                "ANTHROPIC_DEFAULT_HAIKU_MODEL_NAME": "glm-5.1",
                "ANTHROPIC_DEFAULT_FABLE_MODEL_NAME": "glm-5.1",
            }
        })

    def test_prepare_claude_defaults_unset_tiers_to_main_model(self):
        # Regression: a profile that only sets ANTHROPIC_MODEL must still emit
        # every tier var. Claude Code merges --settings with ~/.claude/settings.json,
        # so an omitted tier lets a stale model from a different provider leak
        # through (e.g. minimax profile erroring with "selected model (mimo-v2.5)").
        config = {
            "profiles": {
                "api": {
                    "claude": {
                        "cc-doubao-minimax": {
                            "env": {
                                "ANTHROPIC_BASE_URL": "https://ark.cn-beijing.volces.com/api/coding",
                                "ANTHROPIC_AUTH_TOKEN": "${SECRET_TOKEN}",
                                "ANTHROPIC_MODEL": "minimax-m3",
                            },
                        }
                    }
                }
            }
        }
        argv, env, _, _ = aweswitch.prepare_run(config, "cc-doubao-minimax", [], {"SECRET_TOKEN": "secret"})
        settings_path = argv[2]
        settings_env = json.loads(Path(settings_path).read_text())["env"]

        # Every tier resolves to the provider's own model, never a leaked stale one.
        for tier in ("OPUS", "SONNET", "HAIKU", "FABLE"):
            self.assertEqual(settings_env[f"ANTHROPIC_DEFAULT_{tier}_MODEL"], "minimax-m3")
        # An explicit per-tier override is preserved, not clobbered by the default.
        config["profiles"]["api"]["claude"]["cc-doubao-minimax"]["env"]["ANTHROPIC_DEFAULT_HAIKU_MODEL"] = "minimax-m3-mini"
        argv, _, _, _ = aweswitch.prepare_run(config, "cc-doubao-minimax", [], {"SECRET_TOKEN": "secret"})
        settings_env = json.loads(Path(argv[2]).read_text())["env"]
        self.assertEqual(settings_env["ANTHROPIC_DEFAULT_HAIKU_MODEL"], "minimax-m3-mini")
        self.assertEqual(settings_env["ANTHROPIC_DEFAULT_SONNET_MODEL"], "minimax-m3")

    def test_prepare_claude_ignores_top_level_model(self):
        config = {
            "profiles": {
                "api": {
                    "claude": {
                        "cc-glm": {
                            "model": "ignored-model",
                            "env": {
                                "ANTHROPIC_BASE_URL": "https://example.test",
                                "ANTHROPIC_AUTH_TOKEN": "${SECRET_TOKEN}",
                                "ANTHROPIC_MODEL": "glm-5.1",
                            },
                        }
                    }
                }
            }
        }
        argv, env, _, _ = aweswitch.prepare_run(config, "cc-glm", [], {"SECRET_TOKEN": "secret"})

        self.assertNotIn("ANTHROPIC_MODEL", env)
        self.assertNotIn("ANTHROPIC_BASE_URL", env)
        self.assertNotIn("ANTHROPIC_AUTH_TOKEN", env)
        self.assertNotIn("--model", argv)
        self.assertNotIn("ignored-model", argv)

    def test_prepare_codex_uses_config_overrides_and_env(self):
        config = {
            "profiles": {
                "api": {
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
        }
        base_env = {"PATH": "/bin", "CODEX_BASE": "https://provider.test/v1", "CODEX_KEY": "sk-test"}

        argv, env, _, _ = aweswitch.prepare_run(config, "cx-test", ["--verbose"], base_env)

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
        # API key injected via env; argv carries only the env var NAME (env_key), never the secret
        self.assertEqual(env["OPENAI_API_KEY"], "sk-test")
        self.assertNotIn("sk-test", " ".join(argv))
        # User args passed through
        self.assertIn("--verbose", argv)

    def test_prepare_codex_rejects_missing_base_url(self):
        config = {
            "profiles": {
                "api": {
                    "codex": {
                        "cx-bad": {
                            "env": {
                                "OPENAI_API_KEY": "${KEY}",
                            },
                        }
                    }
                }
            }
        }
        with self.assertRaisesRegex(SystemExit, "OPENAI_BASE_URL is required"):
            aweswitch.prepare_run(config, "cx-bad", [], {"KEY": "sk-test"})

    def test_prepare_codex_rejects_missing_api_key(self):
        config = {
            "profiles": {
                "api": {
                    "codex": {
                        "cx-bad": {
                            "env": {
                                "OPENAI_BASE_URL": "https://example.com/v1",
                            },
                        }
                    }
                }
            }
        }
        with self.assertRaisesRegex(SystemExit, "OPENAI_API_KEY is required"):
            aweswitch.prepare_run(config, "cx-bad", [], {})

    def _make_cx_config(self, models=None):
        env = {
            "OPENAI_BASE_URL": "https://provider.test/v1",
            "OPENAI_API_KEY": "${CX_KEY}",
        }
        if models is not None:
            env["OPENAI_MODEL"] = models
        return {"profiles": {"api": {"codex": {"cx-test": {"env": env}}}}}

    def _c_args(self, argv):
        c_args = []
        i = 1
        while i < len(argv):
            if argv[i] == "-c" and i + 1 < len(argv):
                c_args.append(argv[i + 1])
                i += 2
            else:
                break
        return c_args

    def test_prepare_codex_uses_model_from_args(self):
        config = self._make_cx_config({"gpt-5.2-codex": "GPT-5.2", "kimi-k2.7": "Kimi"})

        argv, env, _, _ = aweswitch.prepare_run(config, "cx-test", ["kimi-k2.7"], {"CX_KEY": "sk-test"})

        self.assertEqual(argv[0], "codex")
        self.assertIn('model="kimi-k2.7"', self._c_args(argv))
        self.assertIn('model_providers.custom.name="custom"', self._c_args(argv))
        self.assertIn('model_providers.custom.env_key="OPENAI_API_KEY"', self._c_args(argv))
        self.assertEqual(env["OPENAI_API_KEY"], "sk-test")

    def test_prepare_codex_defaults_to_first_model(self):
        config = self._make_cx_config({"gpt-5.2-codex": "GPT-5.2", "kimi-k2.7": "Kimi"})

        argv, env, _, _ = aweswitch.prepare_run(config, "cx-test", [], {"CX_KEY": "sk-test"})

        self.assertIn('model="gpt-5.2-codex"', self._c_args(argv))

    def test_prepare_codex_rejects_unknown_model(self):
        config = self._make_cx_config({"gpt-5.2-codex": "GPT-5.2"})

        with self.assertRaisesRegex(SystemExit, "unknown model 'gpt-9.9'"):
            aweswitch.prepare_run(config, "cx-test", ["gpt-9.9"], {"CX_KEY": "sk-test"})

    def test_prepare_codex_matches_model_case_insensitively(self):
        config = self._make_cx_config({"gpt-5.2-codex": "GPT-5.2", "kimi-k2.7": "Kimi"})

        argv, _, _, _ = aweswitch.prepare_run(config, "cx-test", ["GPT-5.2-CODEX"], {"CX_KEY": "sk-test"})

        self.assertIn('model="gpt-5.2-codex"', self._c_args(argv))

    def test_prepare_codex_matches_display_name_case_insensitively(self):
        config = self._make_cx_config({"gpt-5.2-codex": "GPT-5.2"})

        argv, _, _, _ = aweswitch.prepare_run(config, "cx-test", ["gpt-5.2"], {"CX_KEY": "sk-test"})

        self.assertIn('model="gpt-5.2-codex"', self._c_args(argv))

    def test_prepare_codex_matches_model_substring_case_insensitively(self):
        config = self._make_cx_config({"gpt-5.2-codex": "GPT-5.2", "kimi-k2.7": "Kimi"})

        argv, _, _, _ = aweswitch.prepare_run(config, "cx-test", ["GPT"], {"CX_KEY": "sk-test"})

        self.assertIn('model="gpt-5.2-codex"', self._c_args(argv))

    def test_prepare_codex_rejects_ambiguous_substring_match(self):
        config = self._make_cx_config({"gpt-5.2-codex": "GPT-5.2", "gpt-5.1": "GPT-5.1"})

        with self.assertRaisesRegex(SystemExit, "ambiguous model 'gpt'"):
            aweswitch.prepare_run(config, "cx-test", ["gpt"], {"CX_KEY": "sk-test"})

    def test_prepare_codex_rejects_non_string_model_display_name(self):
        config = self._make_cx_config({"gpt-5.2-codex": 42})

        with self.assertRaisesRegex(SystemExit, "model IDs and display names must be non-empty strings"):
            aweswitch.prepare_run(config, "cx-test", ["gpt"], {"CX_KEY": "sk-test"})

    def test_prepare_codex_without_models_keeps_legacy_behavior(self):
        config = self._make_cx_config(models=None)

        argv, env, _, _ = aweswitch.prepare_run(config, "cx-test", ["--verbose"], {"CX_KEY": "sk-test"})

        c_args = self._c_args(argv)
        self.assertNotIn('model="--verbose"', c_args)  # no model injected, arg passes through
        for c in c_args:
            self.assertFalse(c.startswith("model="))
        self.assertIn("--verbose", argv)
        self.assertIn('model_providers.custom.env_key="OPENAI_API_KEY"', c_args)

    def test_prepare_codex_normalizes_string_models(self):
        config = self._make_cx_config("gpt-5.2-codex, kimi-k2.7")

        argv, env, _, _ = aweswitch.prepare_run(config, "cx-test", ["kimi-k2.7"], {"CX_KEY": "sk-test"})

        self.assertIn('model="kimi-k2.7"', self._c_args(argv))

    def test_prepare_rejects_unknown_provider(self):
        config = {
            "profiles": {
                "api": {
                    "unknown": {
                        "test": {"env": {}},
                    }
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

    def test_profile_model_label_shows_string_model_for_codex(self):
        self.assertEqual(
            aweswitch.profile_model_label("codex", {"env": {"OPENAI_MODEL": "auto"}}),
            "auto",
        )

    def test_profile_model_label_shows_list_model_for_codex(self):
        self.assertEqual(
            aweswitch.profile_model_label("codex", {"env": {"OPENAI_MODEL": ["gpt-5.2-codex", "kimi-k2.7"]}}),
            "gpt-5.2-codex, kimi-k2.7",
        )

    def test_profile_model_label_falls_back_to_base_url_for_empty_codex_model(self):
        self.assertEqual(
            aweswitch.profile_model_label("codex", {"env": {"OPENAI_BASE_URL": "https://api.test/v1", "OPENAI_MODEL": ""}}),
            "https://api.test/v1",
        )

    def test_profile_model_label_shows_models_for_codex(self):
        self.assertEqual(
            aweswitch.profile_model_label(
                "codex",
                {"env": {"OPENAI_BASE_URL": "https://api.test/v1",
                         "OPENAI_MODEL": {"kimi-k2.7": "Kimi", "gpt-5.2-codex": "GPT"}}},
            ),
            "gpt-5.2-codex, kimi-k2.7",
        )

    def test_profile_for_errors_on_duplicate_profile_names(self):
        config = {
            "profiles": {
                "api": {
                    "claude": {"default": {"env": {}}},
                    "codex": {"default": {"env": {}}},
                }
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

    @unittest.mock.patch.object(aweswitch.os, "name", "nt")
    @unittest.mock.patch.object(aweswitch.shutil, "which")
    @unittest.mock.patch.object(aweswitch.subprocess, "run")
    @unittest.mock.patch.object(aweswitch.sys, "exit")
    def test_exec_agent_resolves_cmd_on_windows(self, mock_exit, mock_run, mock_which):
        """A bare 'claude' resolves to claude.cmd and is exec'd as-is."""
        mock_which.return_value = r"C:\Users\me\AppData\Roaming\npm\claude.cmd"
        mock_run.return_value = unittest.mock.MagicMock(returncode=0)

        aweswitch.exec_agent(["claude", "--settings", "/tmp/settings.json"], {"PATH": r"C:\Windows"})

        mock_which.assert_called_once_with("claude", path=r"C:\Windows")
        called_argv = mock_run.call_args[0][0]
        self.assertEqual(
            called_argv,
            [r"C:\Users\me\AppData\Roaming\npm\claude.cmd", "--settings", "/tmp/settings.json"],
        )
        mock_exit.assert_called_once_with(0)

    @unittest.mock.patch.object(aweswitch.os, "name", "nt")
    @unittest.mock.patch.object(aweswitch.shutil, "which")
    @unittest.mock.patch.object(aweswitch.subprocess, "run")
    @unittest.mock.patch.object(aweswitch.sys, "exit")
    def test_exec_agent_wraps_ps1_in_powershell_on_windows(self, mock_exit, mock_run, mock_which):
        """A 'claude' that resolves to claude.ps1 is routed through powershell.exe -File."""
        # shutil.which is called twice: first for the user's command, then for powershell itself.
        mock_which.side_effect = [
            r"C:\Users\me\bin\claude.ps1",
            r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe",
        ]
        mock_run.return_value = unittest.mock.MagicMock(returncode=0)

        aweswitch.exec_agent(
            ["claude", "--settings", "/tmp/settings.json"],
            {"PATH": r"C:\Windows"},
        )

        self.assertEqual(mock_which.call_count, 2)
        self.assertEqual(mock_which.call_args_list[0], unittest.mock.call("claude", path=r"C:\Windows"))
        self.assertEqual(mock_which.call_args_list[1][0][0], "powershell")
        called_argv = mock_run.call_args[0][0]
        self.assertEqual(
            called_argv,
            [
                r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe",
                "-NoLogo", "-ExecutionPolicy", "Bypass",
                "-File", r"C:\Users\me\bin\claude.ps1",
                "--settings", "/tmp/settings.json",
            ],
        )
        mock_exit.assert_called_once_with(0)

    @unittest.mock.patch.object(aweswitch.os, "name", "nt")
    @unittest.mock.patch.object(aweswitch.shutil, "which")
    @unittest.mock.patch.object(aweswitch.subprocess, "run")
    @unittest.mock.patch.object(aweswitch.sys, "exit")
    def test_exec_agent_resolves_exe_on_windows(self, mock_exit, mock_run, mock_which):
        """A 'opencode' that resolves to opencode.exe is exec'd as-is (Go binary case)."""
        mock_which.return_value = r"C:\Program Files\opencode\opencode.exe"
        mock_run.return_value = unittest.mock.MagicMock(returncode=0)

        aweswitch.exec_agent(["opencode", "-m", "oc-glm/glm-5.1"], {"PATH": r"C:\Windows"})

        called_argv = mock_run.call_args[0][0]
        self.assertEqual(
            called_argv,
            [r"C:\Program Files\opencode\opencode.exe", "-m", "oc-glm/glm-5.1"],
        )
        mock_exit.assert_called_once_with(0)

    def test_generate_codex_config_produces_valid_toml(self):
        config = aweswitch.generate_codex_config("AiHubMix", "https://aihubmix.com/v1")

        self.assertIn('model_provider = "aihubmix"', config)
        self.assertIn('base_url = "https://aihubmix.com/v1"', config)
        self.assertIn('wire_api = "responses"', config)
        self.assertIn('requires_openai_auth = true', config)
        self.assertIn("[model_providers.aihubmix]", config)


    # --- opencode profiles ---

    def _make_oc_config(self, models=None,
                        base_url="https://example.com/v1", api_key="${OC_KEY}"):
        if models is None:
            models = {"glm-5.1": "GLM-5.1", "glm-5.2": "GLM-5.2"}
        return {
            "profiles": {
                "api": {
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
        }

    def test_prepare_opencode_uses_model_from_args(self):
        config = self._make_oc_config()

        argv, env, oc_info, _ = aweswitch.prepare_run(config, "oc-test", ["glm-5.1"], {"OC_KEY": "sk-test"})

        self.assertEqual(argv[0], "opencode")
        self.assertEqual(argv[1:3], ["-m", "oc-test/glm-5.1"])
        self.assertEqual(env, {"OC_KEY": "sk-test"})
        self.assertEqual(oc_info["provider_name"], "oc-test")
        self.assertEqual(oc_info["model"], "glm-5.1")
        self.assertEqual(oc_info["base_url"], "https://example.com/v1")
        self.assertEqual(oc_info["api_key_ref"], "{env:OC_KEY}")

    def test_prepare_opencode_uses_model_display_name_from_args(self):
        config = self._make_oc_config(models={"peng1/step-router-v1": "step-router-v1"})

        argv, _, oc_info, _ = aweswitch.prepare_run(
            config, "oc-test", ["step-router-v1"], {"OC_KEY": "sk-test"}
        )

        self.assertEqual(argv[1:3], ["-m", "oc-test/peng1/step-router-v1"])
        self.assertEqual(oc_info["model"], "peng1/step-router-v1")

    def test_prepare_opencode_rejects_ambiguous_model_display_name(self):
        config = self._make_oc_config(models={
            "peng1/step-router-v1": "step-router-v1",
            "peng2/step-router-v1": "step-router-v1",
        })

        with self.assertRaisesRegex(SystemExit, "ambiguous model 'step-router-v1'"):
            aweswitch.prepare_run(config, "oc-test", ["step-router-v1"], {"OC_KEY": "sk-test"})

    def test_prepare_opencode_matches_model_case_insensitively(self):
        config = self._make_oc_config(models={"Doubao-Seed-Evolving": "Doubao Seed"})

        argv, _, oc_info, _ = aweswitch.prepare_run(
            config, "oc-test", ["doubao-seed-evolving"], {"OC_KEY": "sk-test"}
        )

        self.assertEqual(argv[1:3], ["-m", "oc-test/Doubao-Seed-Evolving"])
        self.assertEqual(oc_info["model"], "Doubao-Seed-Evolving")

    def test_prepare_opencode_matches_display_name_case_insensitively(self):
        config = self._make_oc_config(models={"hub/seed-evolving": "Seed-Evolving"})

        argv, _, oc_info, _ = aweswitch.prepare_run(
            config, "oc-test", ["seed-evolving"], {"OC_KEY": "sk-test"}
        )

        self.assertEqual(argv[1:3], ["-m", "oc-test/hub/seed-evolving"])
        self.assertEqual(oc_info["model"], "hub/seed-evolving")

    def test_prepare_opencode_rejects_ambiguous_case_insensitive_match(self):
        config = self._make_oc_config(models={"hub/a": "Seed", "hub/b": "seed"})

        with self.assertRaisesRegex(SystemExit, "ambiguous model 'SEED'"):
            aweswitch.prepare_run(config, "oc-test", ["SEED"], {"OC_KEY": "sk-test"})

    def test_prepare_opencode_matches_model_substring_case_insensitively(self):
        config = self._make_oc_config(models={"gpt-5.2-codex": "GPT-5.2 Codex"})

        argv, _, oc_info, _ = aweswitch.prepare_run(
            config, "oc-test", ["GPT"], {"OC_KEY": "sk-test"}
        )

        self.assertEqual(argv[1:3], ["-m", "oc-test/gpt-5.2-codex"])
        self.assertEqual(oc_info["model"], "gpt-5.2-codex")

    def test_prepare_opencode_rejects_ambiguous_substring_match(self):
        config = self._make_oc_config(models={"gpt-5.2": "GPT-5.2", "gpt-5.1": "GPT-5.1"})

        with self.assertRaisesRegex(SystemExit, "ambiguous model 'gpt'"):
            aweswitch.prepare_run(config, "oc-test", ["gpt"], {"OC_KEY": "sk-test"})

    def test_prepare_opencode_passes_extra_args(self):
        config = self._make_oc_config(models={"mimo-v2.5-pro": "MiMo"})

        argv, env, _, _ = aweswitch.prepare_run(config, "oc-test",
                                              ["mimo-v2.5-pro", "--mini"], {"OC_KEY": "sk-test"})

        self.assertEqual(argv[1:3], ["-m", "oc-test/mimo-v2.5-pro"])
        self.assertIn("--mini", argv)
        self.assertNotIn("mimo-v2.5-pro", argv[3:])  # model stripped from extra args

    def test_prepare_opencode_expands_env_refs(self):
        config = self._make_oc_config(api_key="${MY_KEY}")
        base_env = {"MY_KEY": "sk-resolved"}

        argv, env, oc_info, _ = aweswitch.prepare_run(config, "oc-test", ["glm-5.1"], base_env)

        self.assertEqual(oc_info["api_key_ref"], "{env:MY_KEY}")

    def test_prepare_opencode_defaults_to_first_model(self):
        config = self._make_oc_config()

        argv, env, oc_info, _ = aweswitch.prepare_run(config, "oc-test", [], {"OC_KEY": "sk-test"})

        self.assertEqual(argv[1:3], ["-m", "oc-test/glm-5.1"])
        self.assertEqual(oc_info["model"], "glm-5.1")

    def test_prepare_opencode_rejects_unknown_model(self):
        config = self._make_oc_config()

        with self.assertRaisesRegex(SystemExit, "unknown model 'glm-9.9'"):
            aweswitch.prepare_run(config, "oc-test", ["glm-9.9"], {"OC_KEY": "sk-test"})

    def test_prepare_opencode_rejects_missing_base_url(self):
        config = {"profiles": {"api": {"opencode": {"oc-bad": {"env": {
            "OPENCODE_API_KEY": "k", "OPENCODE_MODEL": {"m": "M"},
        }}}}}}

        with self.assertRaisesRegex(SystemExit, "OPENCODE_BASE_URL is required"):
            aweswitch.prepare_run(config, "oc-bad", ["m"], {})

    def test_prepare_opencode_rejects_missing_api_key(self):
        config = {"profiles": {"api": {"opencode": {"oc-bad": {"env": {
            "OPENCODE_BASE_URL": "https://x", "OPENCODE_MODEL": {"m": "M"},
        }}}}}}

        with self.assertRaisesRegex(SystemExit, "OPENCODE_API_KEY is required"):
            aweswitch.prepare_run(config, "oc-bad", ["m"], {})

    def test_prepare_opencode_rejects_empty_model(self):
        config = {"profiles": {"api": {"opencode": {"oc-bad": {"env": {
            "OPENCODE_BASE_URL": "https://x", "OPENCODE_API_KEY": "${OC_KEY}",
            "OPENCODE_MODEL": {},
        }}}}}}

        with self.assertRaisesRegex(
                SystemExit, "OPENCODE_MODEL or OPENCODE_RESPONSES_MODEL is required"):
            aweswitch.prepare_run(config, "oc-bad", ["m"], {"OC_KEY": "sk-test"})

    def test_prepare_opencode_warns_on_plaintext_api_key(self):
        config = self._make_oc_config(api_key="sk-test")

        with unittest.mock.patch("sys.stderr", new=io.StringIO()) as mock_stderr:
            argv, env, oc_info, _ = aweswitch.prepare_run(config, "oc-test", ["glm-5.1"], {})
            self.assertEqual(oc_info["api_key_ref"], "sk-test")
            self.assertIn("tip: OPENCODE_API_KEY is a plain value", mock_stderr.getvalue())

    def test_prepare_opencode_allows_responses_model_without_opencode_model(self):
        config = {"profiles": {"api": {"opencode": {"oc-test": {"env": {
            "OPENCODE_BASE_URL": "https://x/v1", "OPENCODE_API_KEY": "${OC_KEY}",
            "OPENCODE_RESPONSES_MODEL": ["peng1/x", "peng1/y"],
        }}}}}}

        argv, _, oc_info, _ = aweswitch.prepare_run(config, "oc-test", ["peng1/y"], {"OC_KEY": "sk-test"})

        self.assertEqual(argv[-1], "oc-test/peng1/y")
        self.assertEqual(oc_info["model_display_name"], "peng1/y")
        self.assertEqual(oc_info["responses_models"], ["peng1/x", "peng1/y"])

    def test_prepare_opencode_carries_responses_model_list(self):
        config = self._make_oc_config(models={"peng1/x": "x", "peng1/y": "y"})
        config["profiles"]["api"]["opencode"]["oc-test"]["env"]["OPENCODE_RESPONSES_MODEL"] = "ope/openai1"

        _, _, oc_info, _ = aweswitch.prepare_run(
            config, "oc-test", ["ope/openai1"], {"OC_KEY": "sk-test"})

        self.assertEqual(oc_info["responses_models"], ["ope/openai1"])

    def _make_oc_db(self, tmp, session_id, user_models):
        """Create a minimal opencode.db: one session plus user messages.

        user_models entries are "provider/model" stamps, or None for a user
        message without one (pre-model-stamp history).
        """
        import sqlite3
        db = Path(tmp) / "opencode.db"
        conn = sqlite3.connect(db)
        conn.execute("CREATE TABLE session (id TEXT PRIMARY KEY)")
        conn.execute("CREATE TABLE message (session_id TEXT, time_created INTEGER, data TEXT)")
        conn.execute("INSERT INTO session VALUES (?)", (session_id,))
        for i, model in enumerate(user_models):
            data = {"role": "user"}
            if model:
                provider, _, model_id = model.partition("/")
                data["model"] = {"providerID": provider, "modelID": model_id}
            conn.execute(
                "INSERT INTO message VALUES (?, ?, ?)",
                (session_id, 1000 + i, json.dumps(data)),
            )
        conn.commit()
        conn.close()

    def _prepare_oc_resume(self, config, tmp, args):
        with unittest.mock.patch.dict(os.environ, {"OPENCODE_DATA": tmp}):
            with unittest.mock.patch("sys.stderr", new=io.StringIO()) as mock_stderr:
                argv, _, _, _ = aweswitch.prepare_run(
                    config, "oc-test", args, {"OC_KEY": "sk-test"}
                )
        return mock_stderr.getvalue()

    def test_prepare_opencode_warns_when_resume_keeps_previous_model(self):
        config = self._make_oc_config()
        with tempfile.TemporaryDirectory() as tmp:
            self._make_oc_db(tmp, "ses_abc", ["opencode/x-preview-f-free"])

            stderr = self._prepare_oc_resume(
                config, tmp, ["glm-5.1", "-s", "ses_abc"]
            )

            self.assertIn(
                "warning: opencode resumes ses_abc with its previous model "
                "(opencode/x-preview-f-free) and ignores -m",
                stderr,
            )
            self.assertIn("To use oc-test/glm-5.1", stderr)

    def test_prepare_opencode_silent_when_resume_model_matches(self):
        config = self._make_oc_config()
        with tempfile.TemporaryDirectory() as tmp:
            self._make_oc_db(tmp, "ses_abc", ["oc-test/glm-5.1"])

            stderr = self._prepare_oc_resume(
                config, tmp, ["glm-5.1", "-s", "ses_abc"]
            )

            self.assertEqual(stderr, "")

    def test_prepare_opencode_resolves_partial_session_id(self):
        config = self._make_oc_config()
        with tempfile.TemporaryDirectory() as tmp:
            self._make_oc_db(tmp, "ses_abcI", ["opencode/x-preview-f-free"])

            stderr = self._prepare_oc_resume(
                config, tmp, ["glm-5.1", "-s", "ses_abc"]
            )

            self.assertIn("resumes ses_abc with its previous model", stderr)

    def test_prepare_opencode_accepts_long_session_flag(self):
        config = self._make_oc_config()
        with tempfile.TemporaryDirectory() as tmp:
            self._make_oc_db(tmp, "ses_abc", ["opencode/x-preview-f-free"])

            stderr = self._prepare_oc_resume(
                config, tmp, ["glm-5.1", "--session=ses_abc"]
            )

            self.assertIn("resumes ses_abc with its previous model", stderr)

    def test_prepare_opencode_silent_when_last_user_message_lacks_model(self):
        config = self._make_oc_config()
        with tempfile.TemporaryDirectory() as tmp:
            self._make_oc_db(tmp, "ses_abc", [None])

            stderr = self._prepare_oc_resume(
                config, tmp, ["glm-5.1", "-s", "ses_abc"]
            )

            self.assertEqual(stderr, "")

    def test_prepare_opencode_silent_without_session_or_db(self):
        config = self._make_oc_config()
        with tempfile.TemporaryDirectory() as tmp:
            # no -s flag
            self.assertEqual(self._prepare_oc_resume(config, tmp, ["glm-5.1"]), "")
            # -s flag but no opencode.db in the data dir
            self.assertEqual(
                self._prepare_oc_resume(config, tmp, ["glm-5.1", "-s", "ses_missing"]), ""
            )

    def test_parse_version_accepts_prerelease_suffix(self):
        self.assertEqual(update_check._parse_version("0.3.0a1"), (0, 3, 0))
        self.assertTrue(update_check._version_gte("0.3.0a1", "0.3.0"))
        self.assertTrue(update_check._version_gte("0.3.0", "0.3.0a1"))

    def test_write_settings_file_removes_old_temp_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_root = Path(tmp)
            settings_dir = tmp_root / "aweswitch"
            settings_dir.mkdir()
            old_file = settings_dir / "aweswitch-settings-old.json"
            old_file.write_text("{}")
            old_time = time.time() - (25 * 60 * 60)
            os.utime(old_file, (old_time, old_time))

            with unittest.mock.patch("tempfile.gettempdir", return_value=tmp):
                settings_path = aweswitch.write_settings_file({"env": {"A": "B"}})

            self.assertFalse(old_file.exists())
            self.assertTrue(settings_path.exists())
            self.assertEqual(json.loads(settings_path.read_text()), {"env": {"A": "B"}})

    def test_apply_stops_if_backup_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.json"
            settings_path = Path(tmp) / "settings.json"
            settings_path.write_text(json.dumps({"env": {"OLD": "value"}}) + "\n")
            config_path.write_text(json.dumps({
                "profiles": {
                    "api": {
                        "claude": {
                            "cc-test": {
                                "env": {
                                    "ANTHROPIC_BASE_URL": "https://example.test",
                                    "ANTHROPIC_AUTH_TOKEN": "${TOKEN}",
                                    "ANTHROPIC_MODEL": "model",
                                }
                            }
                        }
                    }
                }
            }) + "\n")

            with unittest.mock.patch("aweswitch.cli.claude_settings_path", return_value=settings_path), \
                 unittest.mock.patch("aweswitch.cli.shutil.copy2", side_effect=OSError("disk full")):
                result = CliRunner().invoke(
                    aweswitch.cli,
                    ["apply", "cc-test"],
                    env={"AWESWITCH_CONFIG": str(config_path), "TOKEN": "secret"},
                )

            self.assertNotEqual(result.exit_code, 0)
            self.assertIn("failed to create backup", result.output)
            self.assertEqual(json.loads(settings_path.read_text()), {"env": {"OLD": "value"}})

    def test_apply_claude_creates_missing_settings_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings_path = Path(tmp) / "new-claude-home" / "settings.json"
            config = self._make_apply_config()

            result, _ = self._apply(
                ["apply", "cc-test"], config, tmp,
                extra_env={"CLAUDE_SETTINGS": str(settings_path)},
            )

            self.assertEqual(result.exit_code, 0, result.output)
            self.assertTrue(settings_path.exists())
            self.assert_settings_file_secure(settings_path)

    def test_apply_claude_removes_stale_mutually_exclusive_auth(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings_path = Path(tmp) / "settings.json"
            settings_path.write_text(json.dumps({"env": {
                "ANTHROPIC_API_KEY": "stale",
                "KEEP_ME": "yes",
            }}) + "\n")

            result, _ = self._apply(
                ["apply", "cc-test"], self._make_apply_config(), tmp,
                extra_env={"CLAUDE_SETTINGS": str(settings_path)},
            )

            self.assertEqual(result.exit_code, 0, result.output)
            self.assertIn("Removed stale ANTHROPIC_API_KEY (not in new profile)", result.output)
            env = json.loads(settings_path.read_text())["env"]
            self.assertNotIn("ANTHROPIC_API_KEY", env)
            self.assertEqual(env["ANTHROPIC_AUTH_TOKEN"], "secret")
            self.assertEqual(env["KEEP_ME"], "yes")

    def test_profile_model_label_shows_available_models_for_opencode(self):
        profile = {"env": {"OPENCODE_MODEL": {"glm-5.1": "GLM-5.1", "glm-5.2": "GLM-5.2"}}}
        label = aweswitch.profile_model_label("opencode", profile)
        self.assertIn("glm-5.1", label)
        self.assertIn("glm-5.2", label)

    def test_profile_model_label_shows_string_models_for_opencode(self):
        profile = {"env": {"OPENCODE_MODEL": "glm-5.1, glm-5.2"}}
        label = aweswitch.profile_model_label("opencode", profile)
        self.assertIn("glm-5.1", label)
        self.assertIn("glm-5.2", label)

    def test_profile_model_label_shows_list_models_for_opencode(self):
        profile = {"env": {"OPENCODE_MODEL": ["glm-5.1", "glm-5.2"]}}
        label = aweswitch.profile_model_label("opencode", profile)
        self.assertIn("glm-5.1", label)
        self.assertIn("glm-5.2", label)

    def test_profile_model_label_shows_auto_for_opencode(self):
        profile = {"env": {"OPENCODE_MODEL": "auto"}}
        self.assertEqual(aweswitch.profile_model_label("opencode", profile), "auto")

    def test_init_creates_opencode_profiles(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"

            aweswitch.init_config(path)

            data = json.loads(path.read_text())
            self.assertIn("opencode", data["profiles"]["api"])
            self.assertIn("oc-glm", data["profiles"]["api"]["opencode"])
            env = data["profiles"]["api"]["opencode"]["oc-glm"]["env"]
            self.assertNotIn("OPENCODE_PROVIDER", env)
            self.assertIsInstance(env["OPENCODE_MODEL"], dict)
            self.assertIn("glm-5.1", env["OPENCODE_MODEL"])

    def test_ensure_opencode_provider_creates_new_provider_with_env_ref(self):
        with tempfile.TemporaryDirectory() as tmp:
            oc_path = Path(tmp) / "opencode.json"
            oc_path.write_text(json.dumps({"provider": {}}))

            with unittest.mock.patch("aweswitch.cli.opencode_config_path", return_value=oc_path):
                status = aweswitch.ensure_opencode_provider("https://new.com/v1",
                                                   "{env:MY_KEY}", "oc-doubao", {"doubao-1": "Doubao 1"})

            self.assertEqual(status, "created")
            data = json.loads(oc_path.read_text())
            prov = data["provider"]["oc-doubao"]
            self.assertEqual(prov["options"]["baseURL"], "https://new.com/v1")
            self.assertEqual(prov["options"]["apiKey"], "{env:MY_KEY}")
            self.assertEqual(prov["models"]["doubao-1"]["name"], "Doubao 1")
            self.assertEqual(prov["models"]["doubao-1"]["attachment"], True)
            self.assertEqual(prov["models"]["doubao-1"]["modalities"],
                             {"input": ["text", "image"], "output": ["text"]})
            managed = json.loads(
                oc_path.with_name(".aweswitch-managed-providers.json").read_text()
            )
            self.assertEqual(managed, {"providers": ["oc-doubao"]})
            self.assert_settings_file_secure(
                oc_path.with_name(".aweswitch-managed-providers.json")
            )

    def test_ensure_opencode_provider_backfills_default_modalities(self):
        """Entries written before the modalities/attachment defaults (and fresh
        models) get the declaration on the next write; hand-set values win."""
        with tempfile.TemporaryDirectory() as tmp:
            oc_path = Path(tmp) / "opencode.json"
            oc_path.write_text(json.dumps({"provider": {
                "oc-glm": {
                    "name": "oc-glm",
                    "options": {"baseURL": "https://zhipu.com/v1", "apiKey": "{env:GLM_KEY}"},
                    "models": {
                        "glm-5.1": {"name": "glm-5.1"},
                        "glm-text": {"name": "GLM Text", "attachment": False,
                                     "modalities": {"input": ["text"], "output": ["text"]}},
                    },
                }
            }}))

            with unittest.mock.patch("aweswitch.cli.opencode_config_path", return_value=oc_path):
                status = aweswitch.ensure_opencode_provider("https://zhipu.com/v1",
                                                   "{env:GLM_KEY}", "oc-glm",
                                                   {"glm-5.1": "glm-5.1", "glm-text": "GLM Text"})

            self.assertEqual(status, "updated")
            models = json.loads(oc_path.read_text())["provider"]["oc-glm"]["models"]
            self.assertEqual(models["glm-5.1"], {
                "name": "glm-5.1",
                "attachment": True,
                "modalities": {"input": ["text", "image"], "output": ["text"]},
            })
            self.assertEqual(models["glm-text"], {
                "name": "GLM Text",
                "attachment": False,
                "modalities": {"input": ["text"], "output": ["text"]},
            })

    def test_ensure_opencode_provider_adds_model_to_existing(self):
        with tempfile.TemporaryDirectory() as tmp:
            oc_path = Path(tmp) / "opencode.json"
            oc_path.write_text(json.dumps({"provider": {
                "oc-glm": {
                    "name": "oc-glm",
                    "options": {"baseURL": "https://zhipu.com/v1", "apiKey": "{env:GLM_KEY}"},
                    "models": {"glm-5.1": {"name": "glm-5.1"}},
                }
            }}))

            with unittest.mock.patch("aweswitch.cli.opencode_config_path", return_value=oc_path):
                aweswitch.ensure_opencode_provider("https://zhipu.com/v1",
                                                   "{env:GLM_KEY}", "oc-glm", {"glm-5.2": "glm-5.2"})

            data = json.loads(oc_path.read_text())
            self.assertIn("glm-5.2", data["provider"]["oc-glm"]["models"])
            self.assertIn("glm-5.1", data["provider"]["oc-glm"]["models"])

    def test_ensure_opencode_provider_skips_if_model_exists(self):
        with tempfile.TemporaryDirectory() as tmp:
            oc_path = Path(tmp) / "opencode.json"
            declared = {"name": "glm-5.1", "attachment": True,
                        "modalities": {"input": ["text", "image"], "output": ["text"]}}
            original = {"provider": {
                "oc-glm": {
                    "name": "oc-glm",
                    "options": {"baseURL": "https://zhipu.com/v1", "apiKey": "{env:GLM_KEY}"},
                    "models": {"glm-5.1": declared},
                }
            }
            }
            original_text = json.dumps(original, indent=2) + "\n"
            oc_path.write_text(original_text)

            with unittest.mock.patch("aweswitch.cli.opencode_config_path", return_value=oc_path):
                status = aweswitch.ensure_opencode_provider("https://zhipu.com/v1",
                                                   "{env:GLM_KEY}", "oc-glm", {"glm-5.1": "glm-5.1"})

            self.assertEqual(status, "unchanged")
            self.assertEqual(oc_path.read_text(), original_text)

    def test_ensure_opencode_provider_updates_stale_credentials(self):
        with tempfile.TemporaryDirectory() as tmp:
            oc_path = Path(tmp) / "opencode.json"
            oc_path.write_text(json.dumps({"provider": {
                "oc-glm": {
                    "name": "oc-glm",
                    "options": {"baseURL": "https://old.com/v1", "apiKey": "sk-old"},
                    "models": {"glm-5.1": {"name": "glm-5.1"}},
                }
            }}))

            with unittest.mock.patch("aweswitch.cli.opencode_config_path", return_value=oc_path):
                status = aweswitch.ensure_opencode_provider("https://new.com/v1",
                                                   "{env:NEW_KEY}", "oc-glm", {"glm-5.1": "glm-5.1"})

            self.assertEqual(status, "updated")
            data = json.loads(oc_path.read_text())
            prov = data["provider"]["oc-glm"]
            self.assertEqual(prov["options"]["baseURL"], "https://new.com/v1")
            self.assertEqual(prov["options"]["apiKey"], "{env:NEW_KEY}")
            self.assertIn("glm-5.1", prov["models"])

    def test_ensure_opencode_provider_prunes_models_not_in_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            oc_path = Path(tmp) / "opencode.json"
            oc_path.write_text(json.dumps({"provider": {
                "oc-glm": {
                    "name": "oc-glm",
                    "options": {"baseURL": "https://zhipu.com/v1", "apiKey": "{env:GLM_KEY}"},
                    "models": {"glm-5.1": {"name": "glm-5.1"}, "glm-stale": {"name": "glm-stale"}},
                }
            }}))

            with unittest.mock.patch("aweswitch.cli.opencode_config_path", return_value=oc_path):
                aweswitch.ensure_opencode_provider("https://zhipu.com/v1",
                                                   "{env:GLM_KEY}", "oc-glm",
                                                   {"glm-5.1": "glm-5.1"}, prune=True)

            models = json.loads(oc_path.read_text())["provider"]["oc-glm"]["models"]
            self.assertEqual(list(models), ["glm-5.1"])

    def test_ensure_opencode_provider_repairs_hand_edited_shapes(self):
        """Hand-edited entries (plain-string model, non-object options/models) must
        not crash; they get repaired to the aweswitch shape in place."""
        with tempfile.TemporaryDirectory() as tmp:
            oc_path = Path(tmp) / "opencode.json"
            oc_path.write_text(json.dumps({"provider": {
                "oc-glm": {
                    "options": "oops",
                    "models": {"glm-5.1": "plain string", "keep": {"name": "Keep"}},
                }
            }}))

            with unittest.mock.patch("aweswitch.cli.opencode_config_path", return_value=oc_path):
                status = aweswitch.ensure_opencode_provider("https://zhipu.com/v1",
                                                   "{env:GLM_KEY}", "oc-glm", {"glm-5.1": "GLM-5.1"})

            self.assertEqual(status, "updated")
            prov = json.loads(oc_path.read_text())["provider"]["oc-glm"]
            self.assertEqual(prov["options"]["baseURL"], "https://zhipu.com/v1")
            self.assertEqual(prov["models"]["glm-5.1"], {
                "name": "GLM-5.1",
                "attachment": True,
                "modalities": {"input": ["text", "image"], "output": ["text"]},
            })
            self.assertEqual(prov["models"]["keep"], {"name": "Keep"})

    def test_ensure_opencode_provider_refuses_to_clobber_invalid_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            oc_path = Path(tmp) / "opencode.json"
            original = '{ "provider": { broken json ,,'
            oc_path.write_text(original)

            with unittest.mock.patch("aweswitch.cli.opencode_config_path", return_value=oc_path):
                with self.assertRaisesRegex(SystemExit, "invalid JSON"):
                    aweswitch.ensure_opencode_provider("https://new.com/v1",
                                                       "{env:KEY}", "oc-x", {"m-1": "m-1"})

            self.assertEqual(oc_path.read_text(), original)

    def test_ensure_opencode_provider_reverts_responses_npm_when_flag_off(self):
        with tempfile.TemporaryDirectory() as tmp:
            oc_path = Path(tmp) / "opencode.json"
            oc_path.write_text(json.dumps({"provider": {
                "oc-chat": {
                    "name": "oc-chat",
                    "npm": "@ai-sdk/openai",
                    "options": {"baseURL": "https://x/v1", "apiKey": "{env:KEY}", "setCacheKey": True},
                    "models": {"m-1": {"name": "m-1"}},
                }
            }}))

            with unittest.mock.patch("aweswitch.cli.opencode_config_path", return_value=oc_path):
                status = aweswitch.ensure_opencode_provider("https://x/v1",
                                                            "{env:KEY}", "oc-chat", {"m-1": "m-1"})

            self.assertEqual(status, "updated")
            prov = json.loads(oc_path.read_text())["provider"]["oc-chat"]
            self.assertEqual(prov["npm"], "@ai-sdk/openai-compatible")

    def test_ensure_opencode_provider_leaves_foreign_npm_alone(self):
        with tempfile.TemporaryDirectory() as tmp:
            oc_path = Path(tmp) / "opencode.json"
            oc_path.write_text(json.dumps({"provider": {
                "oc-anthropic": {
                    "name": "oc-anthropic",
                    "npm": "@ai-sdk/anthropic",
                    "options": {"baseURL": "https://x/v1", "apiKey": "{env:KEY}"},
                    "models": {"m-1": {"name": "m-1", "attachment": True,
                                       "modalities": {"input": ["text", "image"], "output": ["text"]}}},
                }
            }}))

            with unittest.mock.patch("aweswitch.cli.opencode_config_path", return_value=oc_path):
                status = aweswitch.ensure_opencode_provider("https://x/v1",
                                                            "{env:KEY}", "oc-anthropic", {"m-1": "m-1"})

            self.assertEqual(status, "unchanged")
            prov = json.loads(oc_path.read_text())["provider"]["oc-anthropic"]
            self.assertEqual(prov["npm"], "@ai-sdk/anthropic")

    def test_opencode_responses_models_parsing(self):
        parse = lambda raw: aweswitch._parse_responses_models(
            raw, "oc-t", "OPENCODE_RESPONSES_MODEL")
        self.assertEqual(parse(None), [])
        self.assertEqual(parse(""), [])
        self.assertEqual(parse([]), [])
        self.assertEqual(parse("peng1/x"), ["peng1/x"])
        self.assertEqual(parse(" peng1/x , peng1/y "), ["peng1/x", "peng1/y"])
        self.assertEqual(parse(["peng1/y"]), ["peng1/y"])
        self.assertEqual(parse(["b", "a", "b"]), ["b", "a"])  # order kept, deduped
        with self.assertRaisesRegex(SystemExit, "OPENCODE_RESPONSES_MODEL must be"):
            parse({"peng1/x": "x"})

    def test_zcode_responses_models_bad_shape_names_zcode_key(self):
        with self.assertRaisesRegex(SystemExit, "ZCODE_RESPONSES_MODEL must be"):
            aweswitch._parse_responses_models(
                {"r1": "R1"}, "zc-t", "ZCODE_RESPONSES_MODEL")

    def test_merge_opencode_models_order_is_deterministic(self):
        # responses-only profile: configured order is the model order
        merged, resp = aweswitch._merge_opencode_models(None, ["b", "a"], "oc-t")
        self.assertEqual(list(merged), ["b", "a"])
        self.assertEqual(resp, ["b", "a"])

        # mixed profile: OPENCODE_MODEL order leads, responses-only appended
        merged, resp = aweswitch._merge_opencode_models(
            {"hub/a": "A", "hub/b": "B"}, "peng1/x", "oc-t")
        self.assertEqual(list(merged), ["hub/a", "hub/b", "peng1/x"])
        with self.assertRaisesRegex(SystemExit, "must not be listed in both"):
            aweswitch._merge_opencode_models(
                {"peng1/x": "X Display"}, "peng1/x,peng1/y", "oc-t")

    def test_zcode_models_map_chat_and_responses_to_model_kind(self):
        models, responses = aweswitch._merge_zcode_models(
            {"chat": "Chat"}, ["response"], "zc-test")

        self.assertEqual(models, {"chat": "Chat", "response": "response"})
        self.assertEqual(responses, ["response"])

    def test_zcode_models_reject_duplicates_between_fields(self):
        with self.assertRaisesRegex(SystemExit, "must not be listed in both"):
            aweswitch._merge_zcode_models("same", ["same"], "zc-test")

    def test_ensure_opencode_provider_stamps_per_model_responses_override(self):
        with tempfile.TemporaryDirectory() as tmp:
            oc_path = Path(tmp) / "opencode.json"
            oc_path.write_text(json.dumps({"provider": {}}))

            with unittest.mock.patch("aweswitch.cli.opencode_config_path", return_value=oc_path):
                status = aweswitch.ensure_opencode_provider(
                    "https://x/v1", "{env:KEY}", "oc-mix",
                    {"peng1/x": "x", "peng1/y": "y"},
                    responses_models={"peng1/x"})

            self.assertEqual(status, "created")
            models = json.loads(oc_path.read_text())["provider"]["oc-mix"]["models"]
            self.assertEqual(models["peng1/x"]["provider"], {"npm": "@ai-sdk/openai"})
            self.assertNotIn("provider", models["peng1/y"])
            self.assertEqual(
                json.loads(oc_path.read_text())["provider"]["oc-mix"]["npm"],
                "@ai-sdk/openai-compatible",
            )

    def test_ensure_opencode_provider_removes_stale_per_model_override(self):
        with tempfile.TemporaryDirectory() as tmp:
            oc_path = Path(tmp) / "opencode.json"
            oc_path.write_text(json.dumps({"provider": {
                "oc-mix": {
                    "name": "oc-mix",
                    "npm": "@ai-sdk/openai-compatible",
                    "options": {"baseURL": "https://x/v1", "apiKey": "{env:KEY}", "setCacheKey": True},
                    "models": {
                        "peng1/x": {"name": "peng1/x", "provider": {"npm": "@ai-sdk/openai"}},
                        "peng1/y": {"name": "y"},
                    },
                }
            }}))

            with unittest.mock.patch("aweswitch.cli.opencode_config_path", return_value=oc_path):
                status = aweswitch.ensure_opencode_provider(
                    "https://x/v1", "{env:KEY}", "oc-mix",
                    {"peng1/x": "x", "peng1/y": "y"})

            self.assertEqual(status, "updated")
            models = json.loads(oc_path.read_text())["provider"]["oc-mix"]["models"]
            self.assertNotIn("provider", models["peng1/x"])

    def test_ensure_opencode_provider_keeps_hand_set_model_npm(self):
        with tempfile.TemporaryDirectory() as tmp:
            oc_path = Path(tmp) / "opencode.json"
            declared = {"attachment": True,
                        "modalities": {"input": ["text", "image"], "output": ["text"]}}
            oc_path.write_text(json.dumps({"provider": {
                "oc-mix": {
                    "name": "oc-mix",
                    "npm": "@ai-sdk/openai-compatible",
                    "options": {"baseURL": "https://x/v1", "apiKey": "{env:KEY}", "setCacheKey": True},
                    "models": {
                        "peng1/x": {"name": "peng1/x", "provider": {"npm": "@ai-sdk/cerebras"}, **declared},
                        "peng1/y": {"name": "peng1/y", **declared},
                    },
                }
            }}))

            with unittest.mock.patch("aweswitch.cli.opencode_config_path", return_value=oc_path):
                status = aweswitch.ensure_opencode_provider(
                    "https://x/v1", "{env:KEY}", "oc-mix",
                    {"peng1/x": "x", "peng1/y": "y"})

            self.assertEqual(status, "unchanged")
            models = json.loads(oc_path.read_text())["provider"]["oc-mix"]["models"]
            self.assertEqual(models["peng1/x"]["provider"], {"npm": "@ai-sdk/cerebras"})

    def test_ensure_opencode_provider_launch_additive_keeps_other_overrides(self):
        with tempfile.TemporaryDirectory() as tmp:
            oc_path = Path(tmp) / "opencode.json"
            oc_path.write_text(json.dumps({"provider": {
                "oc-mix": {
                    "name": "oc-mix",
                    "npm": "@ai-sdk/openai-compatible",
                    "options": {"baseURL": "https://x/v1", "apiKey": "{env:KEY}", "setCacheKey": True},
                    "models": {
                        "peng1/x": {"name": "peng1/x", "provider": {"npm": "@ai-sdk/openai"}},
                    },
                }
            }}))

            with unittest.mock.patch("aweswitch.cli.opencode_config_path", return_value=oc_path):
                # launch of another model (no prune, only that model managed)
                aweswitch.ensure_opencode_provider(
                    "https://x/v1", "{env:KEY}", "oc-mix", {"peng1/y": "y"})

            models = json.loads(oc_path.read_text())["provider"]["oc-mix"]["models"]
            self.assertEqual(models["peng1/x"]["provider"], {"npm": "@ai-sdk/openai"})

    def test_sync_applies_responses_model_overrides(self):
        config = self._make_sync_config()
        env = config["profiles"]["api"]["opencode"]["oc-glm"]["env"]
        env["OPENCODE_RESPONSES_MODEL"] = ["glm-5.3"]

        _, data = self._sync(config)

        models = data["provider"]["oc-glm"]["models"]
        self.assertEqual(models["glm-5.3"]["provider"], {"npm": "@ai-sdk/openai"})
        self.assertNotIn("provider", models["glm-5.1"])

    def test_sync_clearing_responses_model_removes_override(self):
        config = self._make_sync_config()
        env = config["profiles"]["api"]["opencode"]["oc-glm"]["env"]
        env["OPENCODE_RESPONSES_MODEL"] = ["glm-5.3"]

        with tempfile.TemporaryDirectory() as tmp:
            oc_path = Path(tmp) / "opencode.json"
            self._sync(config, oc_path=oc_path)

            del env["OPENCODE_RESPONSES_MODEL"]
            results, data = self._sync(config, oc_path=oc_path)

            self.assertEqual(results[0], ("oc-glm", "updated", 2))
            self.assertNotIn("glm-5.3", data["provider"]["oc-glm"]["models"])

    def test_sync_responses_model_overrides_are_idempotent(self):
        config = self._make_sync_config()
        env = config["profiles"]["api"]["opencode"]["oc-glm"]["env"]
        env["OPENCODE_RESPONSES_MODEL"] = "glm-5.3"

        with tempfile.TemporaryDirectory() as tmp:
            oc_path = Path(tmp) / "opencode.json"
            self._sync(config, oc_path=oc_path)
            text_after_first = oc_path.read_text()

            results, _ = self._sync(config, oc_path=oc_path)

            self.assertEqual(results[0], ("oc-glm", "unchanged", 3))
            self.assertEqual(oc_path.read_text(), text_after_first)

    def test_sync_allows_responses_model_without_opencode_model(self):
        config = self._make_sync_config()
        env = config["profiles"]["api"]["opencode"]["oc-glm"]["env"]
        del env["OPENCODE_MODEL"]
        env["OPENCODE_RESPONSES_MODEL"] = "glm-5.2"

        results, data = self._sync(config)

        self.assertEqual(results[0], ("oc-glm", "created", 1))
        self.assertEqual(
            {m: v["name"] for m, v in data["provider"]["oc-glm"]["models"].items()},
            {"glm-5.2": "glm-5.2"},
        )
        self.assertEqual(
            data["provider"]["oc-glm"]["models"]["glm-5.2"]["provider"],
            {"npm": "@ai-sdk/openai"},
        )

    # --- sync (opencode profiles -> opencode.json) ---

    def _make_sync_config(self):
        return {
            "profiles": {
                "api": {
                    "claude": {
                        "cc-glm": {"env": {"ANTHROPIC_BASE_URL": "https://x", "ANTHROPIC_AUTH_TOKEN": "t"}},
                    },
                    "opencode": {
                        "oc-glm": {"env": {
                            "OPENCODE_BASE_URL": "https://zhipu.com/v1",
                            "OPENCODE_API_KEY": "${GLM_KEY}",
                            "OPENCODE_NAME": "Zhipu GLM",
                            "OPENCODE_MODEL": {"glm-5.1": "GLM-5.1", "glm-5.2": "GLM-5.2"},
                        }},
                        "oc-xiaomi": {"env": {
                            "OPENCODE_BASE_URL": "https://xiaomi.com/v1",
                            "OPENCODE_API_KEY": "${MIMO_KEY}",
                            "OPENCODE_MODEL": ["mimo-v2.5", "mimo-v2.5-pro"],
                        }},
                    },
                }
            }
        }

    def _sync(self, config, names=None, oc_path=None):
        oc_path = oc_path or (Path(tempfile.mkdtemp()) / "opencode.json")
        if not oc_path.exists():
            oc_path.write_text(json.dumps({"provider": {}}))
        with unittest.mock.patch("aweswitch.cli.opencode_config_path", return_value=oc_path):
            results = aweswitch.sync_opencode_profiles(config, names)
        return results, json.loads(oc_path.read_text())

    def test_sync_writes_all_opencode_profiles_with_full_model_lists(self):
        results, data = self._sync(self._make_sync_config())

        self.assertEqual(results, [
            ("oc-glm", "created", 2),
            ("oc-xiaomi", "created", 2),
        ])
        glm = data["provider"]["oc-glm"]
        self.assertEqual(glm["name"], "Zhipu GLM")
        self.assertEqual(glm["options"]["baseURL"], "https://zhipu.com/v1")
        self.assertEqual(glm["options"]["apiKey"], "{env:GLM_KEY}")
        self.assertEqual(
            {m: v["name"] for m, v in glm["models"].items()},
            {"glm-5.1": "GLM-5.1", "glm-5.2": "GLM-5.2"},
        )
        mimo = data["provider"]["oc-xiaomi"]
        self.assertEqual(mimo["name"], "oc-xiaomi")  # no OPENCODE_NAME -> profile name
        self.assertEqual(
            {m: v["name"] for m, v in mimo["models"].items()},
            {"mimo-v2.5": "mimo-v2.5", "mimo-v2.5-pro": "mimo-v2.5-pro"},
        )

    def test_sync_prunes_stale_models_and_updates_credentials(self):
        config = self._make_sync_config()
        with tempfile.TemporaryDirectory() as tmp:
            oc_path = Path(tmp) / "opencode.json"
            oc_path.write_text(json.dumps({"provider": {
                "oc-glm": {
                    "name": "Old Name",
                    "options": {"baseURL": "https://old.com/v1", "apiKey": "sk-old"},
                    "models": {"glm-5.1": {"name": "glm-5.1"}, "glm-stale": {"name": "glm-stale"}},
                },
                "opencode": {"options": {}, "models": {}},  # foreign provider stays untouched
            }}))

            results, data = self._sync(config, oc_path=oc_path)

            self.assertEqual(results[0], ("oc-glm", "updated", 2))
            glm = data["provider"]["oc-glm"]
            self.assertEqual(glm["name"], "Zhipu GLM")
            self.assertEqual(glm["options"]["baseURL"], "https://zhipu.com/v1")
            self.assertEqual(list(glm["models"]), ["glm-5.1", "glm-5.2"])
            self.assertIn("opencode", data["provider"])  # not an aweswitch profile

    def test_sync_named_profiles_only(self):
        results, data = self._sync(self._make_sync_config(), names=["oc-glm"])

        self.assertEqual(results, [("oc-glm", "created", 2)])
        self.assertIn("oc-glm", data["provider"])
        self.assertNotIn("oc-xiaomi", data["provider"])

    def test_sync_second_run_is_unchanged(self):
        config = self._make_sync_config()
        with tempfile.TemporaryDirectory() as tmp:
            oc_path = Path(tmp) / "opencode.json"
            first_results, _ = self._sync(config, oc_path=oc_path)
            text_after_first = oc_path.read_text()

            second_results, _ = self._sync(config, oc_path=oc_path)

            self.assertEqual([r[1] for r in first_results], ["created", "created"])
            self.assertEqual([r[1] for r in second_results], ["unchanged", "unchanged"])
            self.assertEqual(oc_path.read_text(), text_after_first)

    def test_sync_rejects_non_opencode_profile(self):
        with self.assertRaisesRegex(SystemExit, "sync only supports opencode api profiles"):
            self._sync(self._make_sync_config(), names=["cc-glm"])

    def test_sync_rejects_unknown_profile(self):
        with self.assertRaisesRegex(SystemExit, "unknown profile"):
            self._sync(self._make_sync_config(), names=["oc-nope"])

    def test_sync_validates_all_profiles_before_writing_any(self):
        config = self._make_sync_config()
        config["profiles"]["api"]["opencode"]["oc-broken"] = {"env": {
            "OPENCODE_BASE_URL": "${OC_URL_MISSING}",
            "OPENCODE_API_KEY": "${K}",
            "OPENCODE_MODEL": ["m"],
        }}
        with tempfile.TemporaryDirectory() as tmp:
            oc_path = Path(tmp) / "opencode.json"
            oc_path.write_text(json.dumps({"provider": {}}))

            with unittest.mock.patch("aweswitch.cli.opencode_config_path", return_value=oc_path):
                with self.assertRaisesRegex(SystemExit, "OC_URL_MISSING"):
                    aweswitch.sync_opencode_profiles(config)

            # nothing was written even though oc-glm sorted before oc-broken
            self.assertEqual(json.loads(oc_path.read_text()), {"provider": {}})

    # ------------------------------------------------------------------
    # zcode tests
    # ------------------------------------------------------------------

    def test_ensure_zcode_provider_creates_new_provider_with_env_ref(self):
        with tempfile.TemporaryDirectory() as tmp:
            zc_path = Path(tmp) / "config.json"
            zc_path.write_text(json.dumps({"provider": {}}))

            with unittest.mock.patch("aweswitch.cli.zcode_config_path", return_value=zc_path):
                status = aweswitch.ensure_zcode_provider(
                    "https://open.bigmodel.cn/api/anthropic",
                    "{env:GLM_KEY}", "zc-glm",
                    ["GLM-5.3-Flash", "GLM-5-Turbo"],
                    display_name="BigModel - Coding Plan",
                )

            self.assertEqual(status, "created")
            data = json.loads(zc_path.read_text())
            prov = data["provider"]["zc-glm"]
            self.assertEqual(prov["name"], "BigModel - Coding Plan")
            self.assertNotIn("kind", prov)
            self.assertEqual(prov["options"]["baseURL"], "https://open.bigmodel.cn/api/anthropic")
            self.assertEqual(prov["options"]["apiKey"], "{env:GLM_KEY}")
            self.assertTrue(prov["enabled"])
            self.assertEqual(prov["source"], "custom")
            self.assertEqual(prov["models"]["GLM-5.3-Flash"]["name"], "GLM-5.3-Flash")
            self.assertEqual(prov["models"]["GLM-5.3-Flash"]["limit"],
                             {"context": 1000000, "output": 128000})
            self.assertEqual(prov["models"]["GLM-5.3-Flash"]["modalities"],
                             {"input": ["text", "image"], "output": ["text"]})
            self.assertTrue(prov["models"]["GLM-5.3-Flash"]["zcode"]["modalitiesConfigured"])
            self.assertEqual(prov["models"]["GLM-5.3-Flash"]["kind"], "openai-compatible")
            managed = json.loads(
                zc_path.with_name(".aweswitch-managed-providers.json").read_text()
            )
            self.assertEqual(managed, {"providers": ["zc-glm"]})
            self.assert_settings_file_secure(
                zc_path.with_name(".aweswitch-managed-providers.json")
            )

    def test_ensure_zcode_provider_backfills_default_modalities(self):
        with tempfile.TemporaryDirectory() as tmp:
            zc_path = Path(tmp) / "config.json"
            zc_path.write_text(json.dumps({"provider": {
                "zc-glm": {
                    "name": "zc-glm",
                    "kind": "anthropic",
                    "options": {
                        "baseURL": "https://open.bigmodel.cn/api/anthropic",
                        "apiKey": "{env:GLM_KEY}",
                    },
                    "models": {
                        "GLM-5.3-Flash": {"name": "GLM-5.3-Flash"},
                        "GLM-text": {"name": "GLM Text", "modalities": {"input": ["text"], "output": ["text"]}},
                    },
                }
            }}))

            with unittest.mock.patch("aweswitch.cli.zcode_config_path", return_value=zc_path):
                status = aweswitch.ensure_zcode_provider(
                    "https://open.bigmodel.cn/api/anthropic",
                    "{env:GLM_KEY}", "zc-glm",
                    ["GLM-5.3-Flash", "GLM-text"],
                    display_name="BigModel - Coding Plan",
                )

            self.assertEqual(status, "updated")
            models = json.loads(zc_path.read_text())["provider"]["zc-glm"]["models"]
            self.assertEqual(models["GLM-5.3-Flash"], {
                "name": "GLM-5.3-Flash",
                "kind": "openai-compatible",
                "limit": {"context": 1000000, "output": 128000},
                "modalities": {"input": ["text", "image"], "output": ["text"]},
                "zcode": {"modalitiesConfigured": True},
            })
            self.assertEqual(models["GLM-text"], {
                "name": "GLM Text",
                "kind": "openai-compatible",
                "limit": {"context": 1000000, "output": 128000},
                "modalities": {"input": ["text"], "output": ["text"]},
                "zcode": {"modalitiesConfigured": True},
            })

    def test_ensure_zcode_provider_updates_stale_credentials(self):
        with tempfile.TemporaryDirectory() as tmp:
            zc_path = Path(tmp) / "config.json"
            zc_path.write_text(json.dumps({"provider": {
                "zc-glm": {
                    "name": "zc-glm",
                    "kind": "openai",
                    "options": {
                        "baseURL": "https://old.com/v1",
                        "apiKey": "sk-old",
                    },
                    "models": {"GLM-5.3-Flash": {"name": "GLM-5.3-Flash"}},
                }
            }}))

            with unittest.mock.patch("aweswitch.cli.zcode_config_path", return_value=zc_path):
                status = aweswitch.ensure_zcode_provider(
                    "https://open.bigmodel.cn/api/anthropic",
                    "{env:NEW_KEY}", "zc-glm",
                    ["GLM-5.3-Flash"],
                    display_name="BigModel - Coding Plan",
                )

            self.assertEqual(status, "updated")
            data = json.loads(zc_path.read_text())
            prov = data["provider"]["zc-glm"]
            self.assertEqual(prov["options"]["baseURL"], "https://open.bigmodel.cn/api/anthropic")
            self.assertEqual(prov["options"]["apiKey"], "{env:NEW_KEY}")
            self.assertNotIn("kind", prov)
            self.assertEqual(prov["name"], "BigModel - Coding Plan")

    def test_ensure_zcode_provider_prunes_models_not_in_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            zc_path = Path(tmp) / "config.json"
            zc_path.write_text(json.dumps({"provider": {
                "zc-glm": {
                    "name": "zc-glm",
                    "kind": "anthropic",
                    "options": {
                        "baseURL": "https://open.bigmodel.cn/api/anthropic",
                        "apiKey": "{env:GLM_KEY}",
                    },
                    "models": {
                        "GLM-5.3-Flash": {"name": "GLM-5.3-Flash"},
                        "GLM-stale": {"name": "GLM-stale"},
                    },
                }
            }}))

            with unittest.mock.patch("aweswitch.cli.zcode_config_path", return_value=zc_path):
                aweswitch.ensure_zcode_provider(
                    "https://open.bigmodel.cn/api/anthropic",
                    "{env:GLM_KEY}", "zc-glm",
                    ["GLM-5.3-Flash"],
                    prune=True,
                )

            models = json.loads(zc_path.read_text())["provider"]["zc-glm"]["models"]
            self.assertEqual(list(models), ["GLM-5.3-Flash"])

    def test_ensure_zcode_provider_repairs_hand_edited_shapes(self):
        with tempfile.TemporaryDirectory() as tmp:
            zc_path = Path(tmp) / "config.json"
            zc_path.write_text(json.dumps({"provider": {
                "zc-glm": {
                    "options": "oops",
                    "models": {"GLM-5.3-Flash": "plain string", "keep": {"name": "Keep"}},
                }
            }}))

            with unittest.mock.patch("aweswitch.cli.zcode_config_path", return_value=zc_path):
                status = aweswitch.ensure_zcode_provider(
                    "https://open.bigmodel.cn/api/anthropic",
                    "{env:GLM_KEY}", "zc-glm",
                    ["GLM-5.3-Flash"],
                )

            self.assertEqual(status, "updated")
            prov = json.loads(zc_path.read_text())["provider"]["zc-glm"]
            self.assertEqual(prov["options"]["baseURL"], "https://open.bigmodel.cn/api/anthropic")
            self.assertEqual(prov["models"]["GLM-5.3-Flash"]["name"], "GLM-5.3-Flash")
            self.assertTrue(prov["enabled"])
            self.assertEqual(prov["source"], "custom")
            self.assertEqual(prov["models"]["keep"], {"name": "Keep"})

    def test_ensure_zcode_provider_refuses_to_clobber_invalid_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            zc_path = Path(tmp) / "config.json"
            original = '{ "provider": { broken json ,,'
            zc_path.write_text(original)

            with unittest.mock.patch("aweswitch.cli.zcode_config_path", return_value=zc_path):
                with self.assertRaisesRegex(SystemExit, "invalid JSON"):
                    aweswitch.ensure_zcode_provider(
                    "https://x/v1", "{env:KEY}", "zc-x", ["m-1"]
                    )

            self.assertEqual(zc_path.read_text(), original)

    def test_sync_zcode_profiles_writes_all_profiles_with_full_model_lists(self):
        config = {
            "profiles": {
                "api": {
                    "zcode": {
                        "zc-a": {"env": {
                            "ZCODE_BASE_URL": "https://a.test/v1",
                            "ZCODE_API_KEY": "${A_KEY}",
                            "ZCODE_MODEL": {"m1": "M1", "m2": "M2"},
                        }},
                        "zc-b": {"env": {
                            "ZCODE_BASE_URL": "https://b.test/v1",
                            "ZCODE_API_KEY": "${B_KEY}",
                            "ZCODE_MODEL": ["n1", "n2"],
                        }},
                    }
                }
            }
        }
        with tempfile.TemporaryDirectory() as tmp:
            zc_path = Path(tmp) / "config.json"
            zc_path.write_text(json.dumps({"provider": {}}))

            with unittest.mock.patch.dict(os.environ, {"ZCODE_CONFIG": str(zc_path), "A_KEY": "a", "B_KEY": "b"}):
                results = aweswitch.sync_zcode_profiles(config)

            self.assertEqual(len(results), 2)
            self.assertEqual(results[0][0], "zc-a")
            self.assertEqual(results[0][1], "created")
            self.assertEqual(results[0][2], 2)
            self.assertEqual(results[1][0], "zc-b")
            self.assertEqual(results[1][1], "created")
            self.assertEqual(results[1][2], 2)

            data = json.loads(zc_path.read_text())
            self.assertNotIn("kind", data["provider"]["zc-a"])
            self.assertEqual(sorted(data["provider"]["zc-a"]["models"]), ["m1", "m2"])
            self.assertNotIn("kind", data["provider"]["zc-b"])
            self.assertEqual(sorted(data["provider"]["zc-b"]["models"]), ["n1", "n2"])

    def test_sync_zcode_profiles_writes_response_kind_per_model(self):
        config = {
            "profiles": {
                "api": {
                    "zcode": {
                        "zc-mix": {"env": {
                            "ZCODE_BASE_URL": "https://a.test/v1",
                            "ZCODE_API_KEY": "${A_KEY}",
                            "ZCODE_MODEL": ["chat1", "chat2"],
                            "ZCODE_RESPONSES_MODEL": ["resp1"],
                        }},
                    }
                }
            }
        }
        with tempfile.TemporaryDirectory() as tmp:
            zc_path = Path(tmp) / "config.json"
            zc_path.write_text(json.dumps({"provider": {}}))

            with unittest.mock.patch.dict(os.environ, {"ZCODE_CONFIG": str(zc_path), "A_KEY": "a"}):
                aweswitch.sync_zcode_profiles(config)

            models = json.loads(zc_path.read_text())["provider"]["zc-mix"]["models"]
            self.assertEqual(models["chat1"]["kind"], "openai-compatible")
            self.assertEqual(models["chat2"]["kind"], "openai-compatible")
            self.assertEqual(models["resp1"]["kind"], "openai")

    def test_ensure_zcode_provider_reverts_response_kind_when_no_longer_responses(self):
        with tempfile.TemporaryDirectory() as tmp:
            zc_path = Path(tmp) / "config.json"
            zc_path.write_text(json.dumps({"provider": {
                "zc-mix": {
                    "name": "zc-mix",
                    "options": {
                        "baseURL": "https://a.test/v1",
                        "apiKey": "{env:A_KEY}",
                    },
                    "models": {
                        "chat1": {"name": "chat1", "kind": "openai"},
                        "chat2": {"name": "chat2", "kind": "openai-compatible"},
                    },
                }
            }}))

            with unittest.mock.patch("aweswitch.cli.zcode_config_path", return_value=zc_path):
                aweswitch.ensure_zcode_provider(
                    "https://a.test/v1", "{env:A_KEY}", "zc-mix",
                    ["chat1", "chat2"], responses_models=[], prune=True,
                )

            models = json.loads(zc_path.read_text())["provider"]["zc-mix"]["models"]
            self.assertEqual(models["chat1"]["kind"], "openai-compatible")

    def test_sync_zcode_profiles_keeps_api_key_as_env_reference(self):
        config = {
            "profiles": {
                "api": {
                    "zcode": {
                        "zc-secret": {"env": {
                            "ZCODE_BASE_URL": "https://zcode.test/v1",
                            "ZCODE_API_KEY": "${ZCODE_TOKEN}",
                            "ZCODE_MODEL": "m1",
                        }},
                    }
                }
            }
        }
        with tempfile.TemporaryDirectory() as tmp:
            zc_path = Path(tmp) / "config.json"
            zc_path.write_text(json.dumps({"provider": {}}))

            with unittest.mock.patch.dict(os.environ, {
                "ZCODE_CONFIG": str(zc_path),
                "ZCODE_TOKEN": "super-secret",
            }):
                aweswitch.sync_zcode_profiles(config)

            provider = json.loads(zc_path.read_text())["provider"]["zc-secret"]
            self.assertEqual(provider["options"]["apiKey"], "{env:ZCODE_TOKEN}")
            self.assertNotIn("super-secret", zc_path.read_text())

    def test_sync_zcode_rejects_non_zcode_profile(self):
        config = self._make_apply_config()
        with tempfile.TemporaryDirectory() as tmp:
            zc_path = Path(tmp) / "config.json"
            zc_path.write_text(json.dumps({"provider": {}}))
            with unittest.mock.patch.dict(os.environ, {"ZCODE_CONFIG": str(zc_path), "X_KEY": "x"}):
                with self.assertRaisesRegex(SystemExit, "sync only supports zcode api profiles"):
                    aweswitch.sync_zcode_profiles(config, ["oc-test"])

    def test_sync_zcode_requires_model(self):
        config = {
            "profiles": {
                "api": {
                    "zcode": {
                        "zc-x": {"env": {
                            "ZCODE_BASE_URL": "https://x.test/v1",
                            "ZCODE_API_KEY": "${X_KEY}",
                        }},
                    }
                }
            }
        }
        with tempfile.TemporaryDirectory() as tmp:
            zc_path = Path(tmp) / "config.json"
            zc_path.write_text(json.dumps({"provider": {}}))
            with unittest.mock.patch.dict(os.environ, {"ZCODE_CONFIG": str(zc_path)}):
                with self.assertRaisesRegex(SystemExit, "ZCODE_MODEL or ZCODE_RESPONSES_MODEL is required"):
                    aweswitch.sync_zcode_profiles(config)

    def test_sync_zcode_rejects_removed_kind_field(self):
        config = {
            "profiles": {
                "api": {
                    "zcode": {
                        "zc-x": {"env": {
                            "ZCODE_BASE_URL": "https://x.test/v1",
                            "ZCODE_API_KEY": "${X_KEY}",
                            "ZCODE_KIND": "anthropic",
                            "ZCODE_MODEL": "m1",
                        }},
                    }
                }
            }
        }
        with tempfile.TemporaryDirectory() as tmp:
            zc_path = Path(tmp) / "config.json"
            zc_path.write_text(json.dumps({"provider": {}}))
            with unittest.mock.patch.dict(os.environ, {"ZCODE_CONFIG": str(zc_path)}):
                with self.assertRaisesRegex(SystemExit, "ZCODE_KIND is no longer supported"):
                    aweswitch.sync_zcode_profiles(config)

    def test_sync_zcode_prunes_models_not_in_config(self):
        config = {
            "profiles": {
                "api": {
                    "zcode": {
                        "zc-glm": {"env": {
                            "ZCODE_BASE_URL": "https://a.test/v1",
                            "ZCODE_API_KEY": "${A_KEY}",
                            "ZCODE_MODEL": "m1",
                        }},
                    }
                }
            }
        }
        with tempfile.TemporaryDirectory() as tmp:
            zc_path = Path(tmp) / "config.json"
            zc_path.write_text(json.dumps({"provider": {
                "zc-glm": {
                    "name": "zc-glm",
                    "kind": "anthropic",
                    "options": {"baseURL": "https://a.test/v1", "apiKey": "{env:A_KEY}"},
                    "models": {"m1": {"name": "m1"}, "m-stale": {"name": "m-stale"}},
                }
            }}))
            with unittest.mock.patch.dict(os.environ, {"ZCODE_CONFIG": str(zc_path), "A_KEY": "a"}):
                aweswitch.sync_zcode_profiles(config)

            models = json.loads(zc_path.read_text())["provider"]["zc-glm"]["models"]
            self.assertEqual(list(models), ["m1"])

    def test_apply_zcode_profile_upserts_provider(self):
        with tempfile.TemporaryDirectory() as tmp:
            zc_path = Path(tmp) / "config.json"
            config = {
                "profiles": {
                    "api": {
                        "zcode": {
                            "zc-test": {"env": {
                                "ZCODE_BASE_URL": "https://example.test/v1",
                                "ZCODE_API_KEY": "${TOKEN}",
                                "ZCODE_MODEL": {"m1": "M1", "m2": "M2"},
                            }},
                        }
                    }
                }
            }
            (Path(tmp) / "config.json").write_text(json.dumps(config) + "\n")
            env = {
                "AWESWITCH_CONFIG": str(Path(tmp) / "aweswitch-config.json"),
                "ZCODE_CONFIG": str(zc_path),
                "TOKEN": "secret",
            }
            (Path(tmp) / "aweswitch-config.json").write_text(json.dumps(config) + "\n")
            result = CliRunner().invoke(aweswitch.cli, ["apply", "zc-test"], env=env)

            self.assertEqual(result.exit_code, 0, result.output)
            self.assertIn("zc-test: created (2 models)", result.output)
            prov = json.loads(zc_path.read_text())["provider"]["zc-test"]
            self.assertEqual(sorted(prov["models"]), ["m1", "m2"])

            # second apply overwrites to match config
            config["profiles"]["api"]["zcode"]["zc-test"]["env"]["ZCODE_MODEL"] = {"m1": "M1"}
            (Path(tmp) / "aweswitch-config.json").write_text(json.dumps(config) + "\n")
            result = CliRunner().invoke(aweswitch.cli, ["apply", "zc-test"], env=env)

            self.assertEqual(result.exit_code, 0, result.output)
            self.assertIn("zc-test: updated (1 models)", result.output)
            self.assertEqual(list(json.loads(zc_path.read_text())["provider"]["zc-test"]["models"]), ["m1"])

    def test_apply_zcode_flag_applies_all_zcode_profiles(self):
        with tempfile.TemporaryDirectory() as tmp:
            zc_path = Path(tmp) / "config.json"
            config = {
                "profiles": {
                    "api": {
                        "zcode": {
                            "zc-a": {"env": {
                                "ZCODE_BASE_URL": "https://a.test/v1",
                                "ZCODE_API_KEY": "${A_KEY}",
                                "ZCODE_MODEL": "m1",
                            }},
                            "zc-b": {"env": {
                                "ZCODE_BASE_URL": "https://b.test/v1",
                                "ZCODE_API_KEY": "${B_KEY}",
                                "ZCODE_MODEL": "n1",
                            }},
                        }
                    }
                }
            }
            env = {
                "AWESWITCH_CONFIG": str(Path(tmp) / "aweswitch-config.json"),
                "ZCODE_CONFIG": str(zc_path),
                "A_KEY": "a",
                "B_KEY": "b",
            }
            (Path(tmp) / "aweswitch-config.json").write_text(json.dumps(config) + "\n")
            result = CliRunner().invoke(aweswitch.cli, ["apply", "--zcode"], env=env)

            self.assertEqual(result.exit_code, 0, result.output)
            self.assertIn("zc-a: created (1 models)", result.output)
            self.assertIn("zc-b: created (1 models)", result.output)
            self.assertIn("Synced to", result.output)

    def test_apply_zcode_flag_rejects_profile_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            zc_path = Path(tmp) / "config.json"
            config = {
                "profiles": {
                    "api": {
                        "zcode": {
                            "zc-test": {"env": {
                                "ZCODE_BASE_URL": "https://x.test/v1",
                                "ZCODE_API_KEY": "${X_KEY}",
                                "ZCODE_MODEL": "m1",
                            }},
                        }
                    }
                }
            }
            env = {
                "AWESWITCH_CONFIG": str(Path(tmp) / "aweswitch-config.json"),
                "ZCODE_CONFIG": str(zc_path),
                "X_KEY": "x",
            }
            (Path(tmp) / "aweswitch-config.json").write_text(json.dumps(config) + "\n")
            result = CliRunner().invoke(aweswitch.cli, ["apply", "--zcode", "zc-test"], env=env)

            self.assertNotEqual(result.exit_code, 0)
            self.assertIn("pick one", result.output)

    def test_apply_zcode_warns_about_orphaned_aweswitch_provider(self):
        with tempfile.TemporaryDirectory() as tmp:
            zc_path = Path(tmp) / "config.json"
            orphan = {
                "name": "zc-old", "kind": "anthropic",
                "options": {"baseURL": "https://old.com/v1", "apiKey": "sk-old"},
                "models": {"m1": {"name": "m1"}},
            }
            hand_written = {
                "name": "mine", "kind": "openai-compatible",
                "options": {"apiKey": "sk", "baseURL": "https://mine/v1"},
            }
            zc_path.write_text(json.dumps({"provider": {"zc-old": orphan, "mine": hand_written}}))
            managed_path = zc_path.with_name(".aweswitch-managed-providers.json")
            managed_path.write_text(json.dumps({"providers": ["zc-old"]}) + "\n")

            config = {
                "profiles": {
                    "api": {
                        "zcode": {
                            "zc-test": {"env": {
                                "ZCODE_BASE_URL": "https://example.test/v1",
                                "ZCODE_API_KEY": "${TOKEN}",
                                "ZCODE_MODEL": "m1",
                            }},
                        }
                    }
                }
            }
            env = {
                "AWESWITCH_CONFIG": str(Path(tmp) / "aweswitch-config.json"),
                "ZCODE_CONFIG": str(zc_path),
                "TOKEN": "secret",
            }
            (Path(tmp) / "aweswitch-config.json").write_text(json.dumps(config) + "\n")
            result = CliRunner().invoke(aweswitch.cli, ["apply", "--zcode"], env=env)

            self.assertEqual(result.exit_code, 0, result.output)
            self.assertIn("orphaned", result.output)
            self.assertIn("zc-old", result.output)
            self.assertIn("--prune orphans", result.output)
            providers = json.loads(zc_path.read_text())["provider"]
            self.assertIn("zc-old", providers)
            self.assertIn("mine", providers)

    def test_apply_zcode_prune_orphans_removes_only_aweswitch_entries(self):
        with tempfile.TemporaryDirectory() as tmp:
            zc_path = Path(tmp) / "config.json"
            orphan = {
                "name": "zc-old", "kind": "anthropic",
                "options": {"baseURL": "https://old.com/v1", "apiKey": "sk-old"},
                "models": {"m1": {"name": "m1"}},
            }
            hand_written = {
                "name": "mine", "kind": "openai-compatible",
                "options": {"apiKey": "sk", "baseURL": "https://mine/v1"},
            }
            zc_path.write_text(json.dumps({"provider": {"zc-old": orphan, "mine": hand_written}}))
            managed_path = zc_path.with_name(".aweswitch-managed-providers.json")
            managed_path.write_text(json.dumps({"providers": ["zc-old"]}) + "\n")

            config = {
                "profiles": {
                    "api": {
                        "zcode": {
                            "zc-test": {"env": {
                                "ZCODE_BASE_URL": "https://example.test/v1",
                                "ZCODE_API_KEY": "${TOKEN}",
                                "ZCODE_MODEL": "m1",
                            }},
                        }
                    }
                }
            }
            env = {
                "AWESWITCH_CONFIG": str(Path(tmp) / "aweswitch-config.json"),
                "ZCODE_CONFIG": str(zc_path),
                "TOKEN": "secret",
            }
            (Path(tmp) / "aweswitch-config.json").write_text(json.dumps(config) + "\n")
            result = CliRunner().invoke(
                aweswitch.cli, ["apply", "--zcode", "--prune", "orphans"], env=env
            )

            self.assertEqual(result.exit_code, 0, result.output)
            self.assertIn("Pruned provider 'zc-old'", result.output)
            providers = json.loads(zc_path.read_text())["provider"]
            self.assertNotIn("zc-old", providers)
            self.assertIn("zc-test", providers)
            self.assertIn("mine", providers)
            managed = json.loads(
                zc_path.with_name(".aweswitch-managed-providers.json").read_text()
            )["providers"]
            self.assertNotIn("zc-old", managed)
            self.assertIn("zc-test", managed)

    def test_apply_zcode_prune_refuses_invalid_managed_provider_registry(self):
        with tempfile.TemporaryDirectory() as tmp:
            zc_path = Path(tmp) / "config.json"
            original = {"provider": {"manual": {
                "name": "manual", "kind": "openai",
                "options": {"apiKey": "sk", "baseURL": "https://manual/v1"},
            }}}
            zc_path.write_text(json.dumps(original))
            zc_path.with_name(".aweswitch-managed-providers.json").write_text("{broken")

            config = {
                "profiles": {
                    "api": {
                        "zcode": {
                            "zc-test": {"env": {
                                "ZCODE_BASE_URL": "https://example.test/v1",
                                "ZCODE_API_KEY": "${TOKEN}",
                                "ZCODE_MODEL": "m1",
                            }},
                        }
                    }
                }
            }
            env = {
                "AWESWITCH_CONFIG": str(Path(tmp) / "aweswitch-config.json"),
                "ZCODE_CONFIG": str(zc_path),
                "TOKEN": "secret",
            }
            (Path(tmp) / "aweswitch-config.json").write_text(json.dumps(config) + "\n")
            result = CliRunner().invoke(
                aweswitch.cli, ["apply", "--zcode", "--prune", "orphans"], env=env
            )

            self.assertNotEqual(result.exit_code, 0)
            self.assertIn("invalid managed-provider JSON", result.output)
            self.assertEqual(json.loads(zc_path.read_text()), original)

    def test_apply_zcode_named_prune_unknown_name_dies_before_any_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            zc_path = Path(tmp) / "config.json"
            zc_path.write_text(json.dumps({"provider": {}}))
            config = {
                "profiles": {
                    "api": {
                        "zcode": {
                            "zc-test": {"env": {
                                "ZCODE_BASE_URL": "https://example.test/v1",
                                "ZCODE_API_KEY": "${TOKEN}",
                                "ZCODE_MODEL": "m1",
                            }},
                        }
                    }
                }
            }
            env = {
                "AWESWITCH_CONFIG": str(Path(tmp) / "aweswitch-config.json"),
                "ZCODE_CONFIG": str(zc_path),
                "TOKEN": "secret",
            }
            (Path(tmp) / "aweswitch-config.json").write_text(json.dumps(config) + "\n")
            result = CliRunner().invoke(
                aweswitch.cli, ["apply", "--zcode", "--prune", "nope"], env=env
            )

            self.assertNotEqual(result.exit_code, 0)
            self.assertIn("no provider 'nope'", result.output)
            self.assertEqual(
                json.loads(zc_path.read_text()), {"provider": {}},
                "the prune name list must be validated before any sync write",
            )

    def _mixed_apply_env(self, tmp, oc_providers=None, zc_providers=None):
        """One opencode + one zcode profile, with both agent config files staged."""
        config = {
            "profiles": {
                "api": {
                    "opencode": {
                        "oc-test": {"env": {
                            "OPENCODE_BASE_URL": "https://example.test/v1",
                            "OPENCODE_API_KEY": "${OC_KEY}",
                            "OPENCODE_MODEL": {"m1": "M1"},
                        }},
                    },
                    "zcode": {
                        "zc-test": {"env": {
                            "ZCODE_BASE_URL": "https://example.test/v1",
                            "ZCODE_API_KEY": "${TOKEN}",
                            "ZCODE_MODEL": "m1",
                        }},
                    },
                }
            }
        }
        oc_path = Path(tmp) / "opencode.json"
        oc_path.write_text(json.dumps({"provider": oc_providers or {}}))
        zc_path = Path(tmp) / "zcode.json"
        zc_path.write_text(json.dumps({"provider": zc_providers or {}}))
        env = {
            "AWESWITCH_CONFIG": str(Path(tmp) / "aweswitch-config.json"),
            "OPENCODE_CONFIG": str(oc_path),
            "ZCODE_CONFIG": str(zc_path),
            "OC_KEY": "sk-oc",
            "TOKEN": "secret",
        }
        (Path(tmp) / "aweswitch-config.json").write_text(json.dumps(config) + "\n")
        return oc_path, zc_path, env

    def test_apply_mixed_prune_name_resolves_in_opencode_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            oc_path, zc_path, env = self._mixed_apply_env(
                tmp, oc_providers={"stale-oc": {"name": "stale-oc", "models": {}}})

            result = CliRunner().invoke(
                aweswitch.cli,
                ["apply", "oc-test", "zc-test", "--prune", "stale-oc"], env=env)

            self.assertEqual(result.exit_code, 0, result.output)
            self.assertIn("Pruned provider 'stale-oc'", result.output)
            self.assertNotIn("stale-oc", json.loads(oc_path.read_text())["provider"])
            self.assertEqual(
                sorted(json.loads(zc_path.read_text())["provider"]), ["zc-test"])

    def test_apply_mixed_prune_name_resolves_in_zcode_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            oc_path, zc_path, env = self._mixed_apply_env(
                tmp, zc_providers={"stale-zc": {"name": "stale-zc", "models": {}}})

            result = CliRunner().invoke(
                aweswitch.cli,
                ["apply", "oc-test", "zc-test", "--prune", "stale-zc"], env=env)

            self.assertEqual(result.exit_code, 0, result.output)
            self.assertIn("Pruned provider 'stale-zc'", result.output)
            self.assertNotIn("stale-zc", json.loads(zc_path.read_text())["provider"])
            self.assertEqual(
                sorted(json.loads(oc_path.read_text())["provider"]), ["oc-test"])

    def test_apply_mixed_prune_name_in_both_configs_prunes_both(self):
        leftover = {"name": "leftover", "models": {}}
        with tempfile.TemporaryDirectory() as tmp:
            oc_path, zc_path, env = self._mixed_apply_env(
                tmp, oc_providers={"leftover": leftover},
                zc_providers={"leftover": leftover})

            result = CliRunner().invoke(
                aweswitch.cli,
                ["apply", "oc-test", "zc-test", "--prune", "leftover"], env=env)

            self.assertEqual(result.exit_code, 0, result.output)
            self.assertNotIn("leftover", json.loads(oc_path.read_text())["provider"])
            self.assertNotIn("leftover", json.loads(zc_path.read_text())["provider"])

    def test_apply_mixed_prune_unknown_name_dies_before_any_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            oc_path, zc_path, env = self._mixed_apply_env(tmp)
            oc_before, zc_before = oc_path.read_text(), zc_path.read_text()

            result = CliRunner().invoke(
                aweswitch.cli,
                ["apply", "oc-test", "zc-test", "--prune", "nope"], env=env)

            self.assertNotEqual(result.exit_code, 0)
            self.assertIn("no provider 'nope'", result.output)
            self.assertEqual(oc_path.read_text(), oc_before)
            self.assertEqual(zc_path.read_text(), zc_before)

    def test_prepare_run_zcode_rejects_launch(self):
        config = {
            "profiles": {
                "api": {
                    "zcode": {
                        "zc-test": {"env": {
                            "ZCODE_BASE_URL": "https://example.test/v1",
                            "ZCODE_API_KEY": "${TOKEN}",
                            "ZCODE_MODEL": "m1",
                        }},
                    }
                }
            }
        }
        with tempfile.TemporaryDirectory() as tmp:
            env = {
                "AWESWITCH_CONFIG": str(Path(tmp) / "config.json"),
                "TOKEN": "secret",
            }
            (Path(tmp) / "config.json").write_text(json.dumps(config) + "\n")
            with self.assertRaisesRegex(SystemExit, "zcode is a desktop GUI app"):
                aweswitch.prepare_run(aweswitch.load_config(Path(tmp) / "config.json"), "zc-test", [])

    def test_profile_model_label_for_zcode(self):
        # dict
        label = aweswitch.profile_model_label("zcode", {"env": {"ZCODE_MODEL": {"a": "A", "b": "B"}}})
        self.assertEqual(label, "a, b")
        # list
        label = aweswitch.profile_model_label("zcode", {"env": {"ZCODE_MODEL": ["a", "b"]}})
        self.assertEqual(label, "a, b")
        # string
        label = aweswitch.profile_model_label("zcode", {"env": {"ZCODE_MODEL": "a,b"}})
        self.assertEqual(label, "a, b")
        # responses-only profile falls back to ZCODE_RESPONSES_MODEL
        label = aweswitch.profile_model_label(
            "zcode", {"env": {"ZCODE_RESPONSES_MODEL": ["r1", "r2"]}})
        self.assertEqual(label, "r1, r2")
        # empty
        label = aweswitch.profile_model_label("zcode", {"env": {}})
        self.assertEqual(label, "?")

    def test_apply_mixed_apply_rejects_missing_zcode_model_before_writing_codex(self):
        """preflight is supposed to validate every profile before any target
        file changes. A zcode profile missing ZCODE_MODEL must abort the call
        before codex.toml is written — otherwise a mixed apply leaves the
        user with a partial state (codex written, zcode failed)."""
        with tempfile.TemporaryDirectory() as tmp:
            config = self._make_apply_config()
            config["profiles"]["api"]["zcode"] = {
                "zc-x": {"env": {
                    "ZCODE_BASE_URL": "https://z/v1",
                    "ZCODE_API_KEY": "${ZKEY}",
                }},
            }
            codex_path = Path(tmp) / "config.toml"
            codex_path.write_text("# original codex\n")

            result, _ = self._apply(
                ["apply", "cx-glm", "zc-x"], config, tmp,
                extra_env={"CODEX_CONFIG": str(codex_path), "ZKEY": "z"},
            )

            self.assertNotEqual(result.exit_code, 0, result.output)
            self.assertIn("ZCODE_MODEL or ZCODE_RESPONSES_MODEL is required for zc-x", result.output)
            self.assertEqual(
                codex_path.read_text(), "# original codex\n",
                "codex.toml must not be written when zcode preflight fails",
            )

    def test_auto_bookmark_runs_worker_in_detached_child(self):
        """On POSIX the bookmark worker must run in a forked child, because
        os.execvpe() in exec_agent destroys threads before their first poll."""
        if os.name == "nt":
            self.skipTest("POSIX fork path")
        with tempfile.TemporaryDirectory() as tmp:
            marker = Path(tmp) / "done"

            def fake_worker(start_time, category, profile, title):
                marker.write_text(f"{category}/{profile}/{title}")

            with unittest.mock.patch.object(aweswitch, "_bookmark_worker", side_effect=fake_worker):
                aweswitch._auto_bookmark("dev", "cc-x", title="t")

            for _ in range(50):
                if marker.exists():
                    break
                time.sleep(0.1)
            self.assertTrue(marker.exists(), "detached bookmark worker never ran")
            self.assertEqual(marker.read_text(), "dev/cc-x/t")


    # --- official accounts (config schema v2) ---

    def test_load_config_migrates_old_layout(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            path.write_text(json.dumps({
                "profiles": {"claude": {"cc-old": {"env": {"ANTHROPIC_BASE_URL": "https://x"}}}},
            }) + "\n")

            data = aweswitch.load_config(path)

            self.assertEqual(
                data["profiles"]["api"]["claude"]["cc-old"]["env"]["ANTHROPIC_BASE_URL"],
                "https://x",
            )
            saved = json.loads(path.read_text())
            self.assertNotIn("claude", saved["profiles"])
            self.assertTrue((Path(tmp) / "config.json.bak").exists())

    def test_load_config_rejects_mixed_layout(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            path.write_text(json.dumps({
                "profiles": {"api": {}, "claude": {"cc-x": {"env": {}}}},
            }) + "\n")

            with self.assertRaisesRegex(SystemExit, "mixes old and new"):
                aweswitch.load_config(path)

    def test_load_config_keeps_new_layout_untouched(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            original = json.dumps({"profiles": {"api": {}, "accounts": {}}}) + "\n"
            path.write_text(original)

            aweswitch.load_config(path)

            self.assertEqual(path.read_text(), original)

    def test_load_config_keeps_empty_profiles_untouched(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            original = json.dumps({"profiles": {}}) + "\n"
            path.write_text(original)

            aweswitch.load_config(path)

            self.assertEqual(path.read_text(), original)
            self.assertFalse((Path(tmp) / "config.json.bak").exists())

    def test_profile_for_resolves_kind(self):
        config = {
            "profiles": {
                "api": {"claude": {"cc-glm": {"env": {}}}},
                "accounts": {"codex": {"cxo-work": {"auth": {"tokens": {}}}}},
            },
        }

        provider, kind, entry = aweswitch.profile_for(config, "cc-glm")
        self.assertEqual((provider, kind), ("claude", "api"))
        provider, kind, entry = aweswitch.profile_for(config, "cxo-work")
        self.assertEqual((provider, kind), ("codex", "account"))

    def test_profile_for_rejects_name_reused_across_kinds(self):
        config = {
            "profiles": {
                "api": {"claude": {"dup": {"env": {}}}},
                "accounts": {"codex": {"dup": {"auth": {}}}},
            },
        }

        with self.assertRaisesRegex(SystemExit, "ambiguous profile"):
            aweswitch.profile_for(config, "dup")

    def test_prepare_codex_account_sets_private_codex_home(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = {"profiles": {"accounts": {"codex": {
                "cxo-work": {"auth": {"tokens": {"access_token": "t"}}},
            }}}}

            with unittest.mock.patch.dict(os.environ, {"AWESWITCH_CONFIG": str(Path(tmp) / "config.json")}):
                argv, env, _, account_info = aweswitch.prepare_run(config, "cxo-work", ["--verbose"], {})

            self.assertEqual(argv, ["codex", "--verbose"])
            self.assertEqual(env["CODEX_HOME"], str(Path(tmp) / "accounts" / "codex" / "cxo-work"))
            self.assertEqual(account_info["provider"], "codex")
            self.assertEqual(account_info["blob"], {"tokens": {"access_token": "t"}})

    def test_prepare_claude_account_sets_private_config_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = {"profiles": {"accounts": {"claude": {
                "cco-team": {"credentials": {"claudeAiOauth": {"accessToken": "t"}}},
            }}}}

            with unittest.mock.patch.dict(os.environ, {"AWESWITCH_CONFIG": str(Path(tmp) / "config.json")}):
                argv, env, _, account_info = aweswitch.prepare_run(config, "cco-team", [], {})

            self.assertEqual(argv, ["claude"])
            self.assertEqual(env["CLAUDE_CONFIG_DIR"], str(Path(tmp) / "accounts" / "claude" / "cco-team"))
            self.assertEqual(env["CLAUDE_CODE_DONT_USE_KEYCHAIN"], "1")
            self.assertEqual(account_info["provider"], "claude")

    def test_prepare_account_rejects_opencode(self):
        config = {"profiles": {"accounts": {"opencode": {"oco-x": {"auth": {}}}}}}

        with self.assertRaisesRegex(SystemExit, "official accounts are not supported"):
            aweswitch.prepare_run(config, "oco-x", [], {})

    def test_ensure_account_dir_materializes_codex_and_preserves_refreshed_tokens(self):
        with tempfile.TemporaryDirectory() as tmp:
            live_config = Path(tmp) / "codex-config.toml"
            live_config.write_text('model = "gpt-5.2-codex"\n')
            blob = {"tokens": {"access_token": "old"}}
            env = {"AWESWITCH_CONFIG": str(Path(tmp) / "config.json"),
                   "CODEX_CONFIG": str(live_config)}
            with unittest.mock.patch.dict(os.environ, env):
                d = aweswitch.ensure_account_dir("codex", "cxo-work", blob)
                cred = d / "auth.json"
                self.assertEqual(json.loads(cred.read_text()), blob)
                self.assert_settings_file_secure(cred)
                self.assertEqual((d / "config.toml").read_text(), 'model = "gpt-5.2-codex"\n')

                # The CLI refreshes tokens inside the dir; the config blob must not clobber them.
                refreshed = {"tokens": {"access_token": "new"}}
                cred.write_text(json.dumps(refreshed))
                aweswitch.ensure_account_dir("codex", "cxo-work", blob)
                self.assertEqual(json.loads(cred.read_text()), refreshed)

                # force=True reseeds the credentials from the config blob.
                aweswitch.ensure_account_dir("codex", "cxo-work", blob, force=True)
                self.assertEqual(json.loads(cred.read_text()), blob)

    def test_ensure_account_dir_materializes_claude_and_seeds_settings(self):
        with tempfile.TemporaryDirectory() as tmp:
            live_settings = Path(tmp) / "settings.json"
            live_settings.write_text('{"permissions": {}}\n')
            blob = {"claudeAiOauth": {"accessToken": "t"}}
            env = {"AWESWITCH_CONFIG": str(Path(tmp) / "config.json"),
                   "CLAUDE_SETTINGS": str(live_settings)}
            with unittest.mock.patch.dict(os.environ, env):
                d = aweswitch.ensure_account_dir("claude", "cco-team", blob)

            self.assertEqual(json.loads((d / ".credentials.json").read_text()), blob)
            self.assert_settings_file_secure(d / ".credentials.json")
            self.assertEqual(json.loads((d / "settings.json").read_text()), {"permissions": {}})

    def test_ensure_account_dir_removes_provider_overrides_from_seed_configs(self):
        with tempfile.TemporaryDirectory() as tmp:
            claude_settings = Path(tmp) / "settings.json"
            claude_settings.write_text(json.dumps({
                "permissions": {"allow": ["Read"]},
                "env": {
                    "ANTHROPIC_BASE_URL": "https://third-party.example",
                    "ANTHROPIC_AUTH_TOKEN": "secret",
                    "KEEP_ME": "yes",
                },
            }) + "\n")
            codex_config = Path(tmp) / "config.toml"
            codex_config.write_text(
                'model = "gpt-5"\n'
                'model_provider = "relay"\n\n'
                '[model_providers.relay]\n'
                'base_url = "https://third-party.example/v1"\n'
                'wire_api = "responses"\n\n'
                '[mcp_servers.docs]\n'
                'command = "docs-mcp"\n'
            )
            env = {
                "AWESWITCH_CONFIG": str(Path(tmp) / "config.json"),
                "CLAUDE_SETTINGS": str(claude_settings),
                "CODEX_CONFIG": str(codex_config),
            }
            with unittest.mock.patch.dict(os.environ, env):
                claude_dir = aweswitch.ensure_account_dir("claude", "cco-work", {})
                codex_dir = aweswitch.ensure_account_dir("codex", "cxo-work", {})

            seeded_settings = json.loads((claude_dir / "settings.json").read_text())
            self.assertEqual(seeded_settings["permissions"], {"allow": ["Read"]})
            self.assertEqual(seeded_settings["env"], {"KEEP_ME": "yes"})
            seeded_codex = (codex_dir / "config.toml").read_text()
            self.assertIn('model = "gpt-5"', seeded_codex)
            self.assertNotIn("model_provider", seeded_codex)
            self.assertNotIn("model_providers.relay", seeded_codex)
            self.assertIn("[mcp_servers.docs]", seeded_codex)

    def test_account_add_imports_live_codex_credentials(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_file = Path(tmp) / "config.json"
            aweswitch.init_config(config_file)
            live_dir = Path(tmp) / "codex"
            live_dir.mkdir()
            blob = {"tokens": {"access_token": "tok", "refresh_token": "ref"}}
            (live_dir / "auth.json").write_text(json.dumps(blob))

            result = CliRunner().invoke(
                aweswitch.cli, ["account", "add", "codex", "cxo-work"],
                env={"AWESWITCH_CONFIG": str(config_file),
                     "CODEX_CONFIG": str(live_dir / "config.toml")})

            self.assertEqual(result.exit_code, 0, result.output)
            data = json.loads(config_file.read_text())
            self.assertEqual(data["profiles"]["accounts"]["codex"]["cxo-work"]["auth"], blob)
            self.assert_settings_file_secure(config_file)

    def test_account_add_rejects_name_used_by_api_profile(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_file = Path(tmp) / "config.json"
            config_file.write_text(json.dumps({
                "profiles": {"api": {"claude": {"work": {"env": {
                    "ANTHROPIC_BASE_URL": "https://x"}}}}},
            }) + "\n")
            live_dir = Path(tmp) / "codex"
            live_dir.mkdir()
            (live_dir / "auth.json").write_text(json.dumps({"tokens": {}}))

            result = CliRunner().invoke(
                aweswitch.cli, ["account", "add", "codex", "work"],
                env={"AWESWITCH_CONFIG": str(config_file),
                     "CODEX_CONFIG": str(live_dir / "config.toml")})

            self.assertNotEqual(result.exit_code, 0)
            self.assertIn("already used", result.output)

    @unittest.mock.patch("aweswitch.cli.subprocess.run")
    def test_account_login_captures_credentials(self, mock_run):
        with tempfile.TemporaryDirectory() as tmp:
            config_file = Path(tmp) / "config.json"
            aweswitch.init_config(config_file)

            def fake_login(argv, env=None):
                cred_path = Path(env["CODEX_HOME"]) / "auth.json"
                cred_path.write_text(json.dumps({"tokens": {"access_token": "fresh"}}))
                return unittest.mock.MagicMock(returncode=0)

            mock_run.side_effect = fake_login

            result = CliRunner().invoke(
                aweswitch.cli, ["account", "login", "codex", "cxo-work"],
                env={"AWESWITCH_CONFIG": str(config_file)})

            self.assertEqual(result.exit_code, 0, result.output)
            data = json.loads(config_file.read_text())
            self.assertEqual(data["profiles"]["accounts"]["codex"]["cxo-work"]["auth"],
                             {"tokens": {"access_token": "fresh"}})
            login_env = mock_run.call_args.kwargs["env"]
            self.assertEqual(login_env["CODEX_HOME"],
                             str(Path(tmp) / "accounts" / "codex" / "cxo-work"))

    @unittest.mock.patch("aweswitch.cli.subprocess.run")
    def test_account_login_rejects_old_credentials_when_relogin_fails(self, mock_run):
        with tempfile.TemporaryDirectory() as tmp:
            config_file = Path(tmp) / "config.json"
            old_blob = {"tokens": {"access_token": "old"}}
            config_file.write_text(json.dumps({
                "profiles": {"api": {}, "accounts": {"codex": {
                    "cxo-work": {"auth": old_blob},
                }}},
            }) + "\n")
            mock_run.return_value = unittest.mock.MagicMock(returncode=1)

            result = CliRunner().invoke(
                aweswitch.cli, ["account", "login", "codex", "cxo-work"],
                env={"AWESWITCH_CONFIG": str(config_file)})

            self.assertNotEqual(result.exit_code, 0)
            self.assertIn("no credentials captured", result.output)
            saved = json.loads(config_file.read_text())
            self.assertEqual(saved["profiles"]["accounts"]["codex"]["cxo-work"]["auth"], old_blob)

    @unittest.mock.patch("aweswitch.cli.subprocess.run")
    def test_account_login_restores_old_credentials_after_spawn_error(self, mock_run):
        with tempfile.TemporaryDirectory() as tmp:
            config_file = Path(tmp) / "config.json"
            old_blob = {"tokens": {"access_token": "old"}}
            config_file.write_text(json.dumps({
                "profiles": {"api": {}, "accounts": {"codex": {
                    "cxo-work": {"auth": old_blob},
                }}},
            }) + "\n")
            mock_run.side_effect = PermissionError("blocked")

            result = CliRunner().invoke(
                aweswitch.cli, ["account", "login", "codex", "cxo-work"],
                env={"AWESWITCH_CONFIG": str(config_file)})

            self.assertNotEqual(result.exit_code, 0)
            self.assertIn("failed to run codex", result.output)
            runtime_cred = Path(tmp) / "accounts" / "codex" / "cxo-work" / "auth.json"
            self.assertEqual(json.loads(runtime_cred.read_text()), old_blob)

    def test_build_claude_env_names_rejected_profile_kind(self):
        config = {"profiles": {"accounts": {"claude": {
            "cco-work": {"credentials": {}},
        }}}}

        with self.assertRaisesRegex(SystemExit, "provider=claude, kind=account"):
            aweswitch.build_claude_env(config, "cco-work", {})

    def test_account_sync_updates_blob_from_runtime_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_file = Path(tmp) / "config.json"
            config_file.write_text(json.dumps({
                "profiles": {"api": {}, "accounts": {"codex": {
                    "cxo-work": {"auth": {"tokens": {"access_token": "stale"}}},
                }}},
            }) + "\n")
            cred = Path(tmp) / "accounts" / "codex" / "cxo-work" / "auth.json"
            cred.parent.mkdir(parents=True)
            cred.write_text(json.dumps({"tokens": {"access_token": "fresh"}}))

            result = CliRunner().invoke(
                aweswitch.cli, ["account", "sync", "codex", "cxo-work"],
                env={"AWESWITCH_CONFIG": str(config_file)})

            self.assertEqual(result.exit_code, 0, result.output)
            data = json.loads(config_file.read_text())
            self.assertEqual(
                data["profiles"]["accounts"]["codex"]["cxo-work"]["auth"]["tokens"]["access_token"],
                "fresh")

    def test_account_remove_and_purge(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_file = Path(tmp) / "config.json"
            config_file.write_text(json.dumps({
                "profiles": {"api": {}, "accounts": {"codex": {
                    "cxo-work": {"auth": {"tokens": {}}},
                }}},
            }) + "\n")
            cred = Path(tmp) / "accounts" / "codex" / "cxo-work" / "auth.json"
            cred.parent.mkdir(parents=True)
            cred.write_text(json.dumps({"tokens": {}}))

            result = CliRunner().invoke(
                aweswitch.cli, ["account", "remove", "codex", "cxo-work", "--purge"],
                env={"AWESWITCH_CONFIG": str(config_file)})

            self.assertEqual(result.exit_code, 0, result.output)
            data = json.loads(config_file.read_text())
            self.assertNotIn("accounts", data["profiles"])
            self.assertFalse(cred.exists())

    def test_account_remove_rejects_escaping_name_before_mutating_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_file = Path(tmp) / "config.json"
            unsafe_name = "../../outside"
            original = {
                "profiles": {"api": {}, "accounts": {"codex": {
                    unsafe_name: {"auth": {"tokens": {}}},
                }}},
            }
            config_file.write_text(json.dumps(original) + "\n")
            outside = Path(tmp) / "outside"
            outside.mkdir()
            sentinel = outside / "keep.txt"
            sentinel.write_text("keep")

            result = CliRunner().invoke(
                aweswitch.cli, ["account", "remove", "codex", unsafe_name, "--purge"],
                env={"AWESWITCH_CONFIG": str(config_file)})

            self.assertNotEqual(result.exit_code, 0)
            self.assertIn("single path component", result.output)
            self.assertEqual(json.loads(config_file.read_text()), original)
            self.assertEqual(sentinel.read_text(), "keep")

    def test_list_marks_account_kind(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_file = Path(tmp) / "config.json"
            config_file.write_text(json.dumps({
                "profiles": {
                    "api": {"claude": {"cc-glm": {"env": {
                        "ANTHROPIC_BASE_URL": "https://x", "ANTHROPIC_MODEL": "glm-5.1"}}}},
                    "accounts": {"claude": {"cco-team": {"credentials": {"x": 1}}}},
                },
            }) + "\n")

            result = CliRunner().invoke(aweswitch.cli, ["list"],
                                        env={"AWESWITCH_CONFIG": str(config_file)})

            self.assertEqual(result.exit_code, 0, result.output)
            self.assertIn("cc-glm\tclaude\tapi\tglm-5.1", result.output)
            self.assertIn("cco-team\tclaude\taccount\tofficial login", result.output)

    def test_show_redacts_account_blob(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_file = Path(tmp) / "config.json"
            config_file.write_text(json.dumps({
                "profiles": {"api": {}, "accounts": {"claude": {
                    "cco-team": {"credentials": {"claudeAiOauth": {"accessToken": "secret-token"}}},
                }}},
            }) + "\n")

            result = CliRunner().invoke(aweswitch.cli, ["show", "cco-team"],
                                        env={"AWESWITCH_CONFIG": str(config_file)})

            self.assertEqual(result.exit_code, 0, result.output)
            self.assertIn("<redacted>", result.output)
            self.assertNotIn("secret-token", result.output)

    def test_apply_rejects_account_profile(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_file = Path(tmp) / "config.json"
            config_file.write_text(json.dumps({
                "profiles": {"api": {}, "accounts": {"claude": {
                    "cco-team": {"credentials": {"x": 1}},
                }}},
            }) + "\n")

            result = CliRunner().invoke(aweswitch.cli, ["apply", "cco-team"],
                                        env={"AWESWITCH_CONFIG": str(config_file)})

            self.assertNotEqual(result.exit_code, 0)
            self.assertIn("accounts are launch-only", result.output)

    # --- apply: codex (config.toml) ---

    def test_write_codex_config_creates_fresh_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.toml"

            aweswitch.write_codex_config(path, "https://zhipu.com/v1", "GLM_KEY", "glm-5.3")

            text = path.read_text()
            self.assertIn('model = "glm-5.3"', text)
            self.assertIn('model_provider = "custom"', text)
            self.assertIn("disable_response_storage = true", text)
            self.assertIn("[model_providers.custom]", text)
            self.assertIn('base_url = "https://zhipu.com/v1"', text)
            self.assertIn('env_key = "GLM_KEY"', text)

    def test_write_codex_config_updates_existing_and_preserves_unrelated(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.toml"
            path.write_text(
                'model_context_window = 1000000\n'
                'model = "gpt-5.6-luna"\n'
                'model_reasoning_effort = "medium"\n'
                'model_provider = "other"\n'
                '\n'
                '[mcp_servers.fetch]\n'
                'command = "uvx"\n'
                '\n'
                '[model_providers.custom]\n'
                'base_url = "https://old.com/v1"\n'
                '\n'
                '[model_providers.custom.sub]\n'
                'x = 1\n'
                '\n'
                '[projects."/tmp"]\n'
                'trust_level = "trusted"\n'
            )

            aweswitch.write_codex_config(path, "https://zhipu.com/v1", "GLM_KEY", "glm-5.3")

            text = path.read_text()
            self.assertIn('model = "glm-5.3"', text)
            self.assertNotIn('model = "gpt-5.6-luna"', text)
            self.assertIn('model_provider = "custom"', text)
            self.assertNotIn('model_provider = "other"', text)
            # unrelated top-level keys and tables survive untouched
            self.assertIn('model_context_window = 1000000', text)
            self.assertIn('model_reasoning_effort = "medium"', text)
            self.assertIn('[mcp_servers.fetch]', text)
            self.assertIn('[projects."/tmp"]', text)
            # old custom table (and its subtable) replaced with the fresh one
            self.assertNotIn("old.com", text)
            self.assertNotIn("[model_providers.custom.sub]", text)
            self.assertIn('base_url = "https://zhipu.com/v1"', text)
            # exactly one custom table
            self.assertEqual(text.count("[model_providers.custom]"), 1)

    def test_write_codex_config_without_model_leaves_existing_model(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.toml"
            path.write_text('model = "gpt-5.6-luna"\n\n[mcp_servers]\n')

            aweswitch.write_codex_config(path, "https://zhipu.com/v1", "GLM_KEY", None)

            text = path.read_text()
            self.assertIn('model = "gpt-5.6-luna"', text)  # profile has no model -> untouched
            self.assertIn('model_provider = "custom"', text)  # inserted before first table

    def test_write_codex_config_inserts_keys_before_first_table(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.toml"
            path.write_text('[mcp_servers]\ncommand = "uvx"\n')

            aweswitch.write_codex_config(path, "https://x/v1", "K", "m1")

            lines = path.read_text().splitlines()
            # top-level assignments must precede the first table header
            self.assertLess(lines.index('model_provider = "custom"'),
                            lines.index("[mcp_servers]"))

    def test_write_codex_config_ignores_brackets_inside_multiline_strings(self):
        """Lines inside multi-line strings must not count as table headers, or
        top-level keys get inserted at the wrong place (silently joining a
        table) and custom-block detection goes wrong."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.toml"
            path.write_text(
                'model = "gpt-5.6-luna"\n'
                'developer_instructions = """\n'
                "Use rtk skills.\n"
                "[model_providers.custom]\n"     # looks like a header, is string body
                'name = "fake"\n'
                '"""\n'
                '\n'
                '[mcp_servers.fetch]\n'
                'command = "uvx"\n'
            )

            aweswitch.write_codex_config(path, "https://zhipu.com/v1", "GLM_KEY", "glm-5.3")

            text = path.read_text()
            self.assertIn('model = "glm-5.3"', text)
            self.assertIn('name = "fake"', text)      # string body untouched
            self.assertIn("[mcp_servers.fetch]", text)
            # the appended real table (fake one inside the string stays fake)
            self.assertIn('[model_providers.custom]\nname = "custom"\n', text)
            lines = text.splitlines()
            # model key must still be before the FIRST real table
            first_table = min(i for i, l in enumerate(lines) if l.startswith("["))
            self.assertLess(lines.index('model = "glm-5.3"'), first_table)
            try:
                import tomllib  # py3.11+: parse check
            except ModuleNotFoundError:
                tomllib = None
            if tomllib is not None:
                data = tomllib.loads(text)
                self.assertEqual(data["developer_instructions"].count("[model_providers.custom]"), 1)
                self.assertEqual(data["model"], "glm-5.3")
                self.assertEqual(data["model_providers"]["custom"]["base_url"], "https://zhipu.com/v1")

    def _make_apply_config(self):
        return {
            "profiles": {
                "api": {
                    "claude": {
                        "cc-test": {"env": {
                            "ANTHROPIC_BASE_URL": "https://example.test",
                            "ANTHROPIC_AUTH_TOKEN": "${TOKEN}",
                            "ANTHROPIC_MODEL": "model",
                        }},
                    },
                    "codex": {
                        "cx-glm": {"env": {
                            "OPENAI_BASE_URL": "https://zhipu.com/v1",
                            "OPENAI_API_KEY": "${GLM_KEY}",
                            "OPENAI_MODEL": {"glm-5.3": "GLM-5.3", "glm-5.1": "GLM-5.1"},
                        }},
                        "cx-plain": {"env": {
                            "OPENAI_BASE_URL": "https://x/v1",
                            "OPENAI_API_KEY": "sk-plain",
                            "OPENAI_MODEL": ["m-1"],
                        }},
                    },
                    "opencode": {
                        "oc-test": {"env": {
                            "OPENCODE_BASE_URL": "https://example.com/v1",
                            "OPENCODE_API_KEY": "${OC_KEY}",
                            "OPENCODE_MODEL": {"m1": "M1", "m2": "M2"},
                        }},
                    },
                }
            }
        }

    def _apply(self, args, config, tmp, extra_env=None):
        oc_path = Path(tmp) / "opencode.json"
        if not oc_path.exists():
            oc_path.write_text(json.dumps({"provider": {}}))
        env = {
            "AWESWITCH_CONFIG": str(Path(tmp) / "config.json"),
            "OPENCODE_CONFIG": str(oc_path),
            "TOKEN": "secret",
            "GLM_KEY": "sk-glm",
            **(extra_env or {}),
        }
        (Path(tmp) / "config.json").write_text(json.dumps(config) + "\n")
        result = CliRunner().invoke(aweswitch.cli, args, env=env)
        return result, oc_path

    def test_apply_codex_profile_writes_config_and_backup(self):
        with tempfile.TemporaryDirectory() as tmp:
            codex_path = Path(tmp) / "config.toml"
            codex_path.write_text('model = "gpt-5.6-luna"\n\n[mcp_servers]\n')

            result, _ = self._apply(
                ["apply", "cx-glm"], self._make_apply_config(), tmp,
                extra_env={"CODEX_CONFIG": str(codex_path)},
            )

            self.assertEqual(result.exit_code, 0, result.output)
            self.assertIn("Applied cx-glm", result.output)
            self.assertIn("env_key = GLM_KEY", result.output)
            self.assertIn("Backup:", result.output)
            text = codex_path.read_text()
            self.assertIn('model = "glm-5.3"', text)  # first model from the dict
            self.assertIn('base_url = "https://zhipu.com/v1"', text)
            self.assertIn('env_key = "GLM_KEY"', text)
            self.assertIn("[mcp_servers]", text)
            self.assertIn('model = "gpt-5.6-luna"', codex_path.with_suffix(".toml.bak").read_text())

    def test_apply_codex_plain_key_warns_and_uses_openai_env_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            codex_path = Path(tmp) / "config.toml"

            result, _ = self._apply(
                ["apply", "cx-plain"], self._make_apply_config(), tmp,
                extra_env={"CODEX_CONFIG": str(codex_path)},
            )

            self.assertEqual(result.exit_code, 0, result.output)
            self.assertIn("OPENAI_API_KEY is a plain value", result.output)
            self.assertIn('env_key = "OPENAI_API_KEY"', codex_path.read_text())

    def test_apply_opencode_profile_upserts_provider(self):
        with tempfile.TemporaryDirectory() as tmp:
            # provider missing -> created
            result, oc_path = self._apply(["apply", "oc-test"], self._make_apply_config(), tmp)
            self.assertEqual(result.exit_code, 0, result.output)
            self.assertIn("oc-test: created (2 models)", result.output)
            prov = json.loads(oc_path.read_text())["provider"]["oc-test"]
            self.assertEqual(sorted(prov["models"]), ["m1", "m2"])

            # provider exists with a stale model -> overwritten to match config
            prov["models"]["stale"] = {"name": "stale"}
            oc_path.write_text(json.dumps({"provider": {"oc-test": prov}}))
            result, oc_path = self._apply(["apply", "oc-test"], self._make_apply_config(), tmp)
            self.assertIn("oc-test: updated (2 models)", result.output)
            self.assertEqual(
                sorted(json.loads(oc_path.read_text())["provider"]["oc-test"]["models"]),
                ["m1", "m2"],
            )

    def test_apply_opencode_flag_applies_all_opencode_profiles(self):
        with tempfile.TemporaryDirectory() as tmp:
            result, oc_path = self._apply(["apply", "--opencode"], self._make_apply_config(), tmp)

            self.assertEqual(result.exit_code, 0, result.output)
            self.assertIn("oc-test: created (2 models)", result.output)
            self.assertIn("Synced to", result.output)

    def test_apply_without_arguments_or_flag_errors_with_hint(self):
        with tempfile.TemporaryDirectory() as tmp:
            result, oc_path = self._apply(["apply"], self._make_apply_config(), tmp)

            self.assertNotEqual(result.exit_code, 0)
            self.assertIn("--opencode", result.output)
            # nothing was written
            self.assertEqual(json.loads(oc_path.read_text()), {"provider": {}})

    def test_apply_opencode_flag_rejects_profile_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            result, _ = self._apply(["apply", "--opencode", "oc-test"], self._make_apply_config(), tmp)

            self.assertNotEqual(result.exit_code, 0)
            self.assertIn("pick one", result.output)

    def _write_oc_with_orphans(self, oc_path):
        orphan = aweswitch.build_opencode_provider_entry("https://old.com/v1", "{env:OLD_KEY}")
        orphan["models"] = {"peng1/x": {"name": "x"}, "peng1/y": {"name": "y"}}
        hand_written = {
            "name": "mine",
            "npm": "@ai-sdk/openai-compatible",
            "options": {"apiKey": "sk", "baseURL": "https://mine/v1", "setCacheKey": True},
        }
        oc_path.write_text(json.dumps({"provider": {"oc-old": orphan, "mine": hand_written}}))
        managed_path = oc_path.with_name(".aweswitch-managed-providers.json")
        managed_path.write_text(json.dumps({"providers": ["oc-old"]}) + "\n")

    def test_apply_warns_about_orphaned_aweswitch_provider(self):
        with tempfile.TemporaryDirectory() as tmp:
            oc_path = Path(tmp) / "opencode.json"
            self._write_oc_with_orphans(oc_path)

            result, oc_path = self._apply(["apply", "--opencode"], self._make_apply_config(), tmp)

            self.assertEqual(result.exit_code, 0, result.output)
            self.assertIn("orphaned", result.output)
            self.assertIn("oc-old", result.output)
            self.assertIn("--prune orphans", result.output)
            providers = json.loads(oc_path.read_text())["provider"]
            self.assertIn("oc-old", providers)  # warn-only: kept
            self.assertIn("mine", providers)  # identical shape but untracked: never reported

    def test_apply_prune_orphans_removes_only_aweswitch_entries(self):
        with tempfile.TemporaryDirectory() as tmp:
            oc_path = Path(tmp) / "opencode.json"
            self._write_oc_with_orphans(oc_path)

            result, oc_path = self._apply(["apply", "--opencode", "--prune", "orphans"],
                                          self._make_apply_config(), tmp)

            self.assertEqual(result.exit_code, 0, result.output)
            self.assertIn("Pruned provider 'oc-old'", result.output)
            providers = json.loads(oc_path.read_text())["provider"]
            self.assertNotIn("oc-old", providers)
            self.assertIn("oc-test", providers)
            self.assertIn("mine", providers)
            managed = json.loads(
                oc_path.with_name(".aweswitch-managed-providers.json").read_text()
            )["providers"]
            self.assertNotIn("oc-old", managed)
            self.assertIn("oc-test", managed)

    def test_apply_prune_refuses_invalid_managed_provider_registry(self):
        with tempfile.TemporaryDirectory() as tmp:
            oc_path = Path(tmp) / "opencode.json"
            original = {"provider": {"manual": {
                "name": "manual",
                "npm": "@ai-sdk/openai-compatible",
                "options": {"setCacheKey": True},
            }}}
            oc_path.write_text(json.dumps(original))
            oc_path.with_name(".aweswitch-managed-providers.json").write_text("{broken")

            result, _ = self._apply(
                ["apply", "--opencode", "--prune", "orphans"],
                self._make_apply_config(), tmp,
            )

            self.assertNotEqual(result.exit_code, 0)
            self.assertIn("invalid managed-provider JSON", result.output)
            self.assertEqual(json.loads(oc_path.read_text()), original)

    def _write_oc_aweshare_leftovers(self, oc_path):
        """opencode.json as it looks after hand-written aweshare wiring: stale
        aweshare* entries, one unrelated hand-written provider, and the default
        model pointing into the stale one."""
        def entry(models):
            prov = aweswitch.build_opencode_provider_entry("https://hub.test/v1", "sk-old")
            prov["models"] = {mid: {"name": mid} for mid in models}
            return prov

        data = {
            "model": "aweshare-peng/peng1/gpt-5.6-luna",
            "provider": {
                "aweshare": entry(["glm-5.1"]),
                "aweshare2": entry(["glm-5.2"]),
                "aweshare-peng": entry(["peng1/gpt-5.6-luna", "peng1/gpt-5.6-terra"]),
                "aweshare-deepseek": entry(["deepseek-v4"]),
                "aweshare-code": entry(["coder-x"]),
                "mine": entry(["own-m"]),
            },
        }
        oc_path.write_text(json.dumps(data, indent=2) + "\n")
        return data

    def test_apply_prune_named_removes_handwritten_entries(self):
        with tempfile.TemporaryDirectory() as tmp:
            oc_path = Path(tmp) / "opencode.json"
            self._write_oc_aweshare_leftovers(oc_path)

            result, oc_path = self._apply(
                ["apply", "--opencode", "--prune",
                 "aweshare,aweshare2,aweshare-peng,aweshare-deepseek,aweshare-code"],
                self._make_apply_config(), tmp)

            self.assertEqual(result.exit_code, 0, result.output)
            for name in ("aweshare", "aweshare2", "aweshare-peng",
                         "aweshare-deepseek", "aweshare-code"):
                self.assertIn(f"Pruned provider '{name}'", result.output)
            data = json.loads(oc_path.read_text())
            self.assertEqual(sorted(data["provider"]), ["mine", "oc-test"])
            # the default model pointed at a deleted provider -> repaired
            self.assertEqual(data["model"], "oc-test/m1")
            managed = json.loads(
                oc_path.with_name(".aweswitch-managed-providers.json").read_text()
            )["providers"]
            self.assertEqual(managed, ["oc-test"])

    def test_apply_prune_unknown_name_dies_before_any_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            oc_path = Path(tmp) / "opencode.json"
            self._write_oc_aweshare_leftovers(oc_path)
            before = oc_path.read_text()

            result, _ = self._apply(
                ["apply", "--opencode", "--prune", "aweshare,nope"],
                self._make_apply_config(), tmp)

            self.assertNotEqual(result.exit_code, 0)
            self.assertIn("no provider 'nope'", result.output)
            self.assertIn(
                "Available providers: aweshare, aweshare-code, "
                "aweshare-deepseek, aweshare-peng, aweshare2, mine",
                result.output,
            )
            self.assertEqual(oc_path.read_text(), before)  # guards fire before the sync writes

    def test_apply_named_prune_unknown_name_dies_before_any_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            oc_path = Path(tmp) / "opencode.json"
            self._write_oc_aweshare_leftovers(oc_path)
            before = oc_path.read_text()

            result, _ = self._apply(
                ["apply", "oc-test", "--prune", "nope"],
                self._make_apply_config(), tmp)

            self.assertNotEqual(result.exit_code, 0)
            self.assertIn("no provider 'nope'", result.output)
            self.assertEqual(oc_path.read_text(), before)

    def test_apply_prune_backed_profile_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            oc_path = Path(tmp) / "opencode.json"
            self._write_oc_aweshare_leftovers(oc_path)
            data = json.loads(oc_path.read_text())
            data["provider"]["oc-test"] = aweswitch.build_opencode_provider_entry(
                "https://example.com/v1", "{env:OC_KEY}")
            oc_path.write_text(json.dumps(data))
            before = oc_path.read_text()

            result, _ = self._apply(
                ["apply", "--opencode", "--prune", "oc-test"],
                self._make_apply_config(), tmp)

            self.assertNotEqual(result.exit_code, 0)
            self.assertIn("remove that profile from the config", result.output)
            self.assertEqual(oc_path.read_text(), before)

    def test_apply_prune_all_removes_all_unbacked_and_repairs_model(self):
        with tempfile.TemporaryDirectory() as tmp:
            oc_path = Path(tmp) / "opencode.json"
            self._write_oc_aweshare_leftovers(oc_path)

            result, oc_path = self._apply(
                ["apply", "--opencode", "--prune", "all"],
                self._make_apply_config(), tmp)

            self.assertEqual(result.exit_code, 0, result.output)
            for name in ("aweshare", "aweshare2", "aweshare-peng",
                         "aweshare-deepseek", "aweshare-code", "mine"):
                self.assertIn(f"Pruned provider '{name}'", result.output)
            data = json.loads(oc_path.read_text())
            self.assertEqual(list(data["provider"]), ["oc-test"])
            self.assertEqual(data["model"], "oc-test/m1")
            managed = json.loads(
                oc_path.with_name(".aweswitch-managed-providers.json").read_text()
            )["providers"]
            self.assertEqual(managed, ["oc-test"])

    def test_apply_prune_all_without_profiles_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            oc_path = Path(tmp) / "opencode.json"
            self._write_oc_aweshare_leftovers(oc_path)
            before = oc_path.read_text()
            config = self._make_apply_config()
            del config["profiles"]["api"]["opencode"]

            result, _ = self._apply(
                ["apply", "--opencode", "--prune", "all"], config, tmp)

            self.assertNotEqual(result.exit_code, 0)
            self.assertIn("would delete every provider", result.output)
            self.assertEqual(oc_path.read_text(), before)

    def test_apply_prune_all_dry_run_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            oc_path = Path(tmp) / "opencode.json"
            self._write_oc_aweshare_leftovers(oc_path)
            before = oc_path.read_text()

            result, oc_path = self._apply(
                ["apply", "--opencode", "--prune", "all", "--dry-run"],
                self._make_apply_config(), tmp)

            self.assertEqual(result.exit_code, 0, result.output)
            self.assertIn("Dry run: nothing will be written.", result.output)
            self.assertIn("oc-test: would sync (2 models)", result.output)
            self.assertIn(
                "Would prune provider 'aweshare-peng' (peng1/gpt-5.6-luna, peng1/gpt-5.6-terra)",
                result.output,
            )
            self.assertIn("Would prune provider 'mine' (own-m)", result.output)
            self.assertIn(
                "Default model: aweshare-peng/peng1/gpt-5.6-luna -> oc-test/m1",
                result.output,
            )
            self.assertEqual(oc_path.read_text(), before)
            self.assertFalse(oc_path.with_name(".aweswitch-managed-providers.json").exists())

    def test_apply_dry_run_requires_prune_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            result, _ = self._apply(
                ["apply", "--opencode", "--dry-run"],
                self._make_apply_config(), tmp)

            self.assertNotEqual(result.exit_code, 0)
            self.assertIn("--dry-run previews pruning", result.output)

    def test_apply_prune_orphans_repairs_dangling_default_model(self):
        with tempfile.TemporaryDirectory() as tmp:
            oc_path = Path(tmp) / "opencode.json"
            self._write_oc_with_orphans(oc_path)
            data = json.loads(oc_path.read_text())
            data["model"] = "oc-old/peng1/x"
            oc_path.write_text(json.dumps(data))

            result, oc_path = self._apply(
                ["apply", "--opencode", "--prune", "orphans"],
                self._make_apply_config(), tmp)

            self.assertEqual(result.exit_code, 0, result.output)
            self.assertIn("Pruned provider 'oc-old'", result.output)
            self.assertEqual(json.loads(oc_path.read_text())["model"], "oc-test/m1")

    def test_apply_prune_keeps_default_model_pointing_at_live_provider(self):
        with tempfile.TemporaryDirectory() as tmp:
            oc_path = Path(tmp) / "opencode.json"
            self._write_oc_aweshare_leftovers(oc_path)
            data = json.loads(oc_path.read_text())
            data["model"] = "mine/own-m"
            oc_path.write_text(json.dumps(data))

            result, oc_path = self._apply(
                ["apply", "--opencode", "--prune", "aweshare,aweshare2"],
                self._make_apply_config(), tmp)

            self.assertEqual(result.exit_code, 0, result.output)
            self.assertNotIn("Default model:", result.output)
            self.assertEqual(json.loads(oc_path.read_text())["model"], "mine/own-m")

    def test_apply_prune_single_profile_form(self):
        with tempfile.TemporaryDirectory() as tmp:
            oc_path = Path(tmp) / "opencode.json"
            self._write_oc_aweshare_leftovers(oc_path)

            result, oc_path = self._apply(
                ["apply", "oc-test", "--prune", "aweshare"],
                self._make_apply_config(), tmp)

            self.assertEqual(result.exit_code, 0, result.output)
            self.assertIn("Pruned provider 'aweshare'", result.output)
            providers = json.loads(oc_path.read_text())["provider"]
            self.assertNotIn("aweshare", providers)
            self.assertIn("mine", providers)
            self.assertIn("oc-test", providers)

    def test_apply_zcode_prune_all_removes_unbacked(self):
        with tempfile.TemporaryDirectory() as tmp:
            zc_path = Path(tmp) / "zcode.json"
            zc_path.write_text(json.dumps({"provider": {
                "zc-old": {"name": "zc-old", "kind": "anthropic",
                           "options": {"baseURL": "https://old.com/v1", "apiKey": "sk-old"}},
                "mine": {"name": "mine", "kind": "openai-compatible",
                         "options": {"apiKey": "sk", "baseURL": "https://mine/v1"}},
            }}))
            config = self._make_apply_config()
            config["profiles"]["api"]["zcode"] = {
                "zc-test": {"env": {
                    "ZCODE_BASE_URL": "https://example.test/v1",
                    "ZCODE_API_KEY": "${TOKEN}",
                    "ZCODE_MODEL": "m1",
                }},
            }
            result, oc_path = self._apply(
                ["apply", "--zcode", "--prune", "all"],
                config, tmp, extra_env={"ZCODE_CONFIG": str(zc_path)})

            self.assertEqual(result.exit_code, 0, result.output)
            self.assertIn("Pruned provider 'zc-old'", result.output)
            self.assertIn("Pruned provider 'mine'", result.output)
            providers = json.loads(zc_path.read_text())["provider"]
            self.assertEqual(list(providers), ["zc-test"])

    def test_ensure_opencode_provider_displays_namespaced_ids_in_full(self):
        with tempfile.TemporaryDirectory() as tmp:
            oc_path = Path(tmp) / "opencode.json"
            oc_path.write_text(json.dumps({"provider": {}}))

            with unittest.mock.patch.dict(os.environ, {"OPENCODE_CONFIG": str(oc_path)}):
                aweswitch.ensure_opencode_provider(
                    "https://hub.example/v1", "{env:HUB_KEY}", "oc-hub",
                    {"hub/x": "x", "hub/y": "Custom Y", "plain": "Plain"})

            models = json.loads(oc_path.read_text())["provider"]["oc-hub"]["models"]
            self.assertEqual(
                {mid: m["name"] for mid, m in models.items()},
                {"hub/x": "hub/x", "hub/y": "Custom Y", "plain": "Plain"},
            )

    def test_apply_mixed_providers_in_one_call(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings_path = Path(tmp) / "settings.json"
            codex_path = Path(tmp) / "config.toml"
            result, oc_path = self._apply(
                ["apply", "cc-test", "cx-glm", "oc-test"], self._make_apply_config(), tmp,
                extra_env={"CLAUDE_SETTINGS": str(settings_path), "CODEX_CONFIG": str(codex_path)},
            )

            self.assertEqual(result.exit_code, 0, result.output)
            self.assertIn("Applied cc-test", result.output)
            self.assertIn("Applied cx-glm", result.output)
            self.assertIn("oc-test: created", result.output)
            self.assertTrue(settings_path.exists())
            self.assertIn("[model_providers.custom]", codex_path.read_text())
            self.assertIn("oc-test", json.loads(oc_path.read_text())["provider"])

    def test_apply_preflights_all_profiles_before_any_write(self):
        config = self._make_apply_config()
        config["profiles"]["accounts"] = {
            "claude": {"acct": {"credentials": {"x": 1}}},
        }
        with tempfile.TemporaryDirectory() as tmp:
            settings_path = Path(tmp) / "settings.json"
            result, _ = self._apply(
                ["apply", "cc-test", "acct"], config, tmp,
                extra_env={"CLAUDE_SETTINGS": str(settings_path)},
            )

            self.assertNotEqual(result.exit_code, 0)
            self.assertIn("accounts are launch-only", result.output)
            self.assertFalse(settings_path.exists())

    def test_apply_rejects_two_codex_profiles(self):
        config = self._make_apply_config()
        config["profiles"]["api"]["codex"]["cx-two"] = dict(config["profiles"]["api"]["codex"]["cx-glm"])
        with tempfile.TemporaryDirectory() as tmp:
            result, _ = self._apply(["apply", "cx-glm", "cx-two"], config, tmp)

            self.assertNotEqual(result.exit_code, 0)
            self.assertIn("apply one codex profile at a time", result.output)

    def test_apply_rejects_two_claude_profiles(self):
        config = self._make_apply_config()
        config["profiles"]["api"]["claude"]["cc-two"] = dict(config["profiles"]["api"]["claude"]["cc-test"])
        with tempfile.TemporaryDirectory() as tmp:
            result, _ = self._apply(["apply", "cc-test", "cc-two"], config, tmp)

            self.assertNotEqual(result.exit_code, 0)
            self.assertIn("apply one claude profile at a time", result.output)

    def test_config_backup_creates_backup_and_prints_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings_path = Path(tmp) / "settings.json"
            settings_path.write_text('{"env": {"OLD": "1"}}\n')

            with unittest.mock.patch("aweswitch.cli.claude_settings_path", return_value=settings_path):
                result = CliRunner().invoke(aweswitch.cli, ["config", "backup"])

            backup_path = settings_path.with_suffix(".json.bak")
            self.assertEqual(result.exit_code, 0)
            self.assertIn(str(backup_path), result.output)
            self.assertEqual(json.loads(backup_path.read_text()), {"env": {"OLD": "1"}})

    def test_config_backup_does_not_overwrite_without_force(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings_path = Path(tmp) / "settings.json"
            settings_path.write_text('{"env": {"NEW": "2"}}\n')
            backup_path = settings_path.with_suffix(".json.bak")
            backup_path.write_text('{"env": {"OLD": "1"}}\n')

            with unittest.mock.patch("aweswitch.cli.claude_settings_path", return_value=settings_path):
                no_force = CliRunner().invoke(aweswitch.cli, ["config", "backup"])

            self.assertEqual(no_force.exit_code, 0)
            self.assertIn("not overwritten", no_force.output)
            self.assertEqual(json.loads(backup_path.read_text()), {"env": {"OLD": "1"}})

            with unittest.mock.patch("aweswitch.cli.claude_settings_path", return_value=settings_path):
                forced = CliRunner().invoke(aweswitch.cli, ["config", "backup", "--force"])

            self.assertEqual(forced.exit_code, 0)
            self.assertEqual(json.loads(backup_path.read_text()), {"env": {"NEW": "2"}})

    def test_config_backup_fails_without_settings(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings_path = Path(tmp) / "settings.json"

            with unittest.mock.patch("aweswitch.cli.claude_settings_path", return_value=settings_path):
                result = CliRunner().invoke(aweswitch.cli, ["config", "backup"])

            self.assertNotEqual(result.exit_code, 0)
            self.assertIn("no settings file found", result.output)

    def test_config_restore_default_uses_bak(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings_path = Path(tmp) / "settings.json"
            settings_path.write_text('{"env": {"NEW": "2"}}\n')
            backup_path = settings_path.with_suffix(".json.bak")
            backup_path.write_text('{"env": {"OLD": "1"}}\n')

            with unittest.mock.patch("aweswitch.cli.claude_settings_path", return_value=settings_path):
                result = CliRunner().invoke(aweswitch.cli, ["config", "restore"])

            self.assertEqual(result.exit_code, 0)
            self.assertEqual(json.loads(settings_path.read_text()), {"env": {"OLD": "1"}})

    def test_config_restore_from_explicit_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings_path = Path(tmp) / "settings.json"
            settings_path.write_text('{"env": {"NEW": "2"}}\n')
            snapshot = Path(tmp) / "settings.json.backup.2026-01-01T00-00-00Z"
            snapshot.write_text('{"env": {"ANCIENT": "0"}}\n')

            with unittest.mock.patch("aweswitch.cli.claude_settings_path", return_value=settings_path):
                result = CliRunner().invoke(aweswitch.cli, ["config", "restore", str(snapshot)])

            self.assertEqual(result.exit_code, 0)
            self.assertEqual(json.loads(settings_path.read_text()), {"env": {"ANCIENT": "0"}})

    def test_config_restore_missing_backup_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings_path = Path(tmp) / "settings.json"

            with unittest.mock.patch("aweswitch.cli.claude_settings_path", return_value=settings_path):
                result = CliRunner().invoke(aweswitch.cli, ["config", "restore", str(Path(tmp) / "missing.json")])

            self.assertNotEqual(result.exit_code, 0)
            self.assertIn("no such backup file", result.output)

    def test_redact_masks_account_blobs_whole(self):
        data = {"profiles": {"accounts": {"codex": {
            "cxo-work": {"auth": {"account_id": "acc", "tokens": {"access_token": "t"}}},
        }}}}

        redacted = aweswitch.redact(data)

        self.assertEqual(redacted["profiles"]["accounts"]["codex"]["cxo-work"]["auth"], "<redacted>")

    def test_should_skip_empty_args(self):
        self.assertTrue(update_check._should_skip([]))


if __name__ == "__main__":
    unittest.main()
