# BACprop

[![pipeline status](https://gitlab.com/freshollie/bacprop/badges/master/pipeline.svg)](https://gitlab.com/freshollie/bacprop/commits/master)
[![coverage report](https://gitlab.com/freshollie/bacprop/badges/master/coverage.svg)](http://freshollie.gitlab.io/bacprop)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/python/black)

A MQTT to BACnet relay. Translating IoT data into virtual sensors on a bacnet network.

## Usage

Running `bacprop` on a local network will allow IoT devices to send MQTT data representing sensor data to
`bacprop` where the sensor will be represented as a BACnet object on the same network.

The sensor must send a JSON MQTT message on the channel `sensor/<sensorId>`. The JSON object keys
will be translated to the properties of the BACnet Object, with the sensorId as the ID of the object.

A sensor message might look like:

```json
{
  "sensorId": 2,
  "temp": 5.3,
  "co2": 502
}
```

`bacprop` will mark faultly any sensor object which it has no received data from
after 10 minutes, as specified in the `bacprop/service.py` definition.

## Developing

`bacprop` is developed using `pipenv`

`pipenv install --dev` will install all requirements for development to take place.

## Testing

`bacprop` is 100% unit tested, and all changes should continue this.

`pipenv run python -m bacprop` can be used to test changes

`pipenv run test` will run all tests

## Running

`pipenv install` will install all requirements for running

`pipenv run python -m bacprop`

## Docker

Docker images have been provided for `bacprop`. Both an armv6 image and a x86 image exist.

## License

`MIT`
