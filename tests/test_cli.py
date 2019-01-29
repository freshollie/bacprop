from bacprop import cli
from bacprop.service import BacPropagator
from pytest_mock import MockFixture


class TestCli:
    def test_service_init(self, mocker: MockFixture) -> None:
        mock_service = mocker.patch("bacprop.cli.BacPropagator")
        cli.main()

        mock_service.assert_called_once()

    def test_service_start(self, mocker: MockFixture) -> None:
        mock_init = mocker.patch("bacprop.cli.BacPropagator")

        mock_service = mocker.create_autospec(BacPropagator)
        mock_init.return_value = mock_service

        cli.main()

        mock_service.start.assert_called_once()
