import pytest
from django.core.management import call_command, CommandError


@pytest.mark.django_db
def test_seed_production_without_version_tag_raises(settings, tmp_path):
    # ENV=production без --version-tag должен падать
    settings.ENVIRONMENT = "production"

    empty_dir = tmp_path / "fixtures"
    empty_dir.mkdir()

    with pytest.raises(CommandError) as ei:
        call_command(
            "seed_customs_rates",
            "--path",
            str(empty_dir),
            "--dry-run",
        )
    assert "Refusing to seed rates in production" in str(ei.value)


@pytest.mark.django_db
def test_seed_production_with_version_tag_allows(settings, tmp_path):
    # ENV=production c --version-tag должен выполняться (даже если файлов нет)
    settings.ENVIRONMENT = "production"

    empty_dir = tmp_path / "fixtures"
    empty_dir.mkdir()

    # Должно завершиться без исключений и просто вывести предупреждение об отсутствии файлов
    call_command(
        "seed_customs_rates",
        "--path",
        str(empty_dir),
        "--version-tag",
        "release_2025_08_17",
        "--dry-run",
    )
