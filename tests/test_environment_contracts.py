from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def read_project_file(name: str) -> str:
    return (PROJECT_ROOT / name).read_text(encoding="utf-8")


def test_base_compose_has_no_fixed_container_names_or_host_ports():
    compose = read_project_file("docker-compose.yml")

    assert "container_name:" not in compose
    assert "    ports:" not in compose


def test_test_runner_does_not_depend_on_napcat():
    compose = read_project_file("docker-compose.test.yml")
    test_service = compose.split("  test:", 1)[1].split("  frontend-test:", 1)[0]

    assert "napcat" not in test_service.lower()
    assert "DB_HOST: mysql" in test_service


def test_environment_examples_and_overrides_exist():
    required_files = [
        ".env.dev.example",
        ".env.test.example",
        ".env.prod.example",
        "docker-compose.dev.yml",
        "docker-compose.test.yml",
        "docker-compose.prod.yml",
    ]

    assert all((PROJECT_ROOT / name).is_file() for name in required_files)


def test_production_example_does_not_contain_the_old_fixed_token():
    old_token = "s~N9cCeg-SDmpwWM"
    production_example = read_project_file(".env.prod.example")

    assert old_token not in production_example
    assert "CHANGE_ME" not in production_example
    assert old_token not in read_project_file("pyproject.toml")


def test_production_secret_template_values_are_empty():
    values = dict(
        line.split("=", 1)
        for line in read_project_file(".env.prod.example").splitlines()
        if line and not line.startswith("#") and "=" in line
    )

    required_runtime_values = [
        "NAPCAT_IMAGE",
        "DB_ROOT_PASSWORD",
        "DB_PASSWORD",
        "ONEBOT_ACCESS_TOKEN",
        "BOT_QQ",
    ]

    assert all(values[name] == "" for name in required_runtime_values)
