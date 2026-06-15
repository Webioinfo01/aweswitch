import json
import os
import stat
import sys
import tempfile
import unittest
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
            self.assertNotIn("codex", data["profiles"])

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

    def test_save_profile_adds_new_profile(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            aweswitch.init_config(path)

            aweswitch.save_profile(path, "my-profile", {
                "ANTHROPIC_BASE_URL": "https://example.com",
                "ANTHROPIC_AUTH_TOKEN": "${MY_TOKEN}",
                "ANTHROPIC_MODEL": "test-model",
            })

            data = json.loads(path.read_text())
            profile = data["profiles"]["claude"]["my-profile"]
            self.assertEqual(profile["env"]["ANTHROPIC_BASE_URL"], "https://example.com")
            self.assertEqual(profile["env"]["ANTHROPIC_AUTH_TOKEN"], "${MY_TOKEN}")
            self.assertEqual(profile["env"]["ANTHROPIC_MODEL"], "test-model")

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
            })

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
            })
            with self.assertRaisesRegex(SystemExit, "already exists"):
                aweswitch.save_profile(path, "dup", {
                    "ANTHROPIC_BASE_URL": "https://other.com",
                    "ANTHROPIC_AUTH_TOKEN": "${T}",
                    "ANTHROPIC_MODEL": "m",
                })

    def test_add_command_creates_profile(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            aweswitch.init_config(path)

            result = CliRunner().invoke(aweswitch.cli, [
                "add",
            ], input="test-profile\nhttps://example.com\nMY_TOKEN\ntest-model\n\n\n\n",
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
            ], input="full-profile\nhttps://example.com\nMY_TOKEN\nmy-model\nhaiku-m\nsonnet-m\n",
                env={"AWESWITCH_CONFIG": str(path)})

            self.assertEqual(result.exit_code, 0, result.output)

            data = json.loads(path.read_text())
            env = data["profiles"]["claude"]["full-profile"]["env"]
            self.assertEqual(env["ANTHROPIC_DEFAULT_HAIKU_MODEL"], "haiku-m")
            self.assertEqual(env["ANTHROPIC_DEFAULT_SONNET_MODEL"], "sonnet-m")

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

        argv, env = aweswitch.prepare_run(config, "cc-glm", ["--verbose"], base_env)

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

        argv, env = aweswitch.prepare_run(config, "cc-glm", [], {}, claude_settings_env)

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

        argv, env = aweswitch.prepare_run(config, "cc-glm", [], base_env)

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

        argv, env = aweswitch.prepare_run(config, "cc-glm", [], {})

        self.assertEqual(env, {})
        self.assertNotIn("--model", argv)
        self.assertNotIn("ignored-model", argv)

    def test_prepare_rejects_codex_profiles_for_now(self):
        config = {
            "profiles": {
                "codex": {
                    "codex-mini": {
                        "model": "gpt-5.4-mini",
                        "env": {"OPENAI_API_KEY": "${OPENAI_API_KEY}"},
                    }
                }
            }
        }

        with self.assertRaisesRegex(SystemExit, "unsupported provider"):
            aweswitch.prepare_run(config, "codex-mini", ["--help"], {})

    def test_profile_model_label_uses_anthropic_model_for_claude(self):
        self.assertEqual(
            aweswitch.profile_model_label("claude", {"env": {"ANTHROPIC_MODEL": "glm-5.1"}}),
            "glm-5.1",
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

    def test_expand_env_errors_on_missing_variable(self):
        with self.assertRaisesRegex(SystemExit, "missing environment variable"):
            aweswitch.expand_value("${MISSING_ENV}", {})

    def test_editor_argv_splits_editor_with_flags(self):
        argv = aweswitch.editor_argv("code -w", Path("/tmp/config.json"))

        self.assertEqual(argv, ["code", "-w", str(Path("/tmp/config.json"))])

    def test_exec_agent_reports_missing_command(self):
        with self.assertRaisesRegex(SystemExit, "command not found"):
            aweswitch.exec_agent(["/tmp/aweswitch-command-that-does-not-exist"], {})


if __name__ == "__main__":
    unittest.main()
