# BACprop

A MQTT to BACnet relay. Translating IoT data into virtual sensors on a bacnet network.

## Developing

`bacprop` is developed using `pipenv`

`pipenv install --dev` will install all requirements for development to take place.

`pipenv run python -m bacprop` can be used to test changes

`pipenv run test` will run all tests

## Running

`pipenv install` will install all requirements for running

`pipenv run python -m bacprop`

## Docker

Docker images have been provided for `bacprop`. Both an armv6 image and a x86 image exist.
