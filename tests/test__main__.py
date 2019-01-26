from pytest_mock import MockFixture


def test_calls_cli(mocker: MockFixture) -> None:
    mock_main = mocker.patch("bacprop.cli.main")

    import bacprop.__main__

    mock_main.assert_called_once()

