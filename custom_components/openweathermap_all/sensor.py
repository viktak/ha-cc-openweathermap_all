"""Platform for sensor integration."""

import logging
from datetime import timedelta, datetime, timezone
import json
import requests
import voluptuous as vol

from homeassistant.components.sensor import PLATFORM_SCHEMA
import homeassistant.helpers.config_validation as cv
from homeassistant.const import (CONF_API_KEY, CONF_LATITUDE, CONF_LONGITUDE)
from homeassistant.util import Throttle
from homeassistant.helpers.entity import Entity

import owm2json

_LOGGER = logging.getLogger(__name__)

MIN_TIME_BETWEEN_UPDATES = timedelta(minutes=10)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_API_KEY): cv.string,
    vol.Required(CONF_LATITUDE): cv.string,
    vol.Required(CONF_LONGITUDE): cv.string,
    # vol.Required("api_list"): cv.ensure_list,
})

SENSOR_PREFIX_ROOT = 'OWM '
SENSOR_PREFIX_POLLUTION = 'Pollution '

SENSOR_TYPES = {
    'co': ['Carbon monoxide (CO)', 'μg/m3', 'mdi:molecule-co'],
    'no': ['Nitrogen monoxide (NO)', 'μg/m3', 'mdi:smog'],
    'no2': ['Nitrogen dioxide (NO2)', 'μg/m3', 'mdi:smog'],
    'o3': ['Ozone (O3)', 'μg/m3', 'mdi:skull-outline'],
    'so2': ['Sulphur dioxide (SO2)', 'μg/m3', 'mdi:smog'],
    'nh3': ['Ammonia (NH3)', 'μg/m3', 'mdi:skull'],
    'pm2_5': ['Fine particles (PM2.5)', 'μg/m3', 'mdi:grain'],
    'pm10': ['Coarse particles (PM10)', 'μg/m3', 'mdi:grain'],
    'aqi': ['Overall Air Quality', '', 'mdi:lungs'],
    'uvi': ['Ultraviolet index', 'idx', 'mdi:hazard-lights'],
    'forecast': ['Forecast', '', 'mdi:eye-arrow-right'],
}


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the sensor platform."""
    lat = config.get(CONF_LATITUDE)
    lon = config.get(CONF_LONGITUDE)
    appid = config.get(CONF_API_KEY)
    api_list = ["air_pollution/forecast"]

    try:
        data = OwmPollutionData(api_list, lat, lon, appid)
    except requests.exceptions.HTTPError as error:
        _LOGGER.error(error)
        return False

    entities = []

    for resource in SENSOR_TYPES:
        sensor_type = resource.lower()
        entities.append(OwmPollutionSensor(data, sensor_type))

    async_add_entities(entities)


class OwmPollutionData(object):

    def __init__(self, api_list, lat, lon, appid):
        self._state = None
        self.lat = lat
        self.lon = lon
        self.appid = appid
        self.data = None
        self.api_list = api_list

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self, sensorType):
        _LOGGER.debug("Updating OWM pollution sensors")
        _LOGGER.debug("sensorType: " + sensorType)
        myOWM = owm2json.owmRequestor(self.api_list, self.lat, self.lon, self.appid)
        try:
            self.data = json.loads(myOWM.GetData())
        except requests.exceptions.RequestException as exc:
            _LOGGER.error("Error occurred while fetching data: %r", exc)
            self.data = None
            return False


class OwmPollutionSensor(Entity):
    """Representation of a Sensor."""

    def __init__(self, data, sensor_type):
        """Initialize the sensor."""
        self.data = data
        self.type = sensor_type
        if self.type == "uvi":
            self._name = SENSOR_PREFIX_ROOT + SENSOR_TYPES[self.type][0]
        else:
            self._name = SENSOR_PREFIX_ROOT + SENSOR_PREFIX_POLLUTION + SENSOR_TYPES[self.type][0]
        self._unit = SENSOR_TYPES[self.type][1]
        self._icon = SENSOR_TYPES[self.type][2]
        self._state = None
        self._extra_state_attributes = None

    @property
    def name(self):
        return self._name

    @property
    def icon(self):
        return self._icon

    @property
    def state(self):
        return self._state

    @property
    def unit_of_measurement(self):
        return self._unit

    @property
    def extra_state_attributes(self):
        return self._extra_state_attributes

    def update(self):
        """Fetch new state data for the sensor.

        This is the only method that should fetch new data for Home Assistant.
        """
        self.data.update(self.type)

        owmData = self.data.data

        # _LOGGER.debug("pollutionData = %s", pollutionData)

        try:

            #   air_pollution

            if self.type == 'co':
                self._state = float(owmData["air_pollution/forecast"]["list"][0]["components"]["co"])

            elif self.type == 'no':
                self._state = float(owmData["air_pollution/forecast"]["list"][0]["components"]["no"])

            elif self.type == 'no2':
                self._state = float(owmData["air_pollution/forecast"]["list"][0]["components"]["no2"])

            elif self.type == 'o3':
                self._state = float(owmData["air_pollution/forecast"]["list"][0]["components"]["o3"])

            elif self.type == 'so2':
                self._state = float(owmData["air_pollution/forecast"]["list"][0]["components"]["so2"])

            elif self.type == 'nh3':
                self._state = float(owmData["air_pollution/forecast"]["list"][0]["components"]["nh3"])

            elif self.type == 'pm2_5':
                self._state = float(owmData["air_pollution/forecast"]["list"][0]["components"]["pm2_5"])

            elif self.type == 'pm10':
                self._state = float(owmData["air_pollution/forecast"]["list"][0]["components"]["pm10"])

            elif self.type == 'aqi':
                self._state = float(owmData["air_pollution/forecast"]["list"][0]["main"]["aqi"])

            #   onecall

            elif self.type == 'uvi':
                self._state = float(owmData["onecall"]["current"]["uvi"])

            elif self.type == 'forecast':
                self._state = float(owmData["air_pollution/forecast"]["list"][0]["main"]["aqi"])
                self._extra_state_attributes = {"forecast": []}
                for f in owmData["air_pollution/forecast"]["list"]:
                    fdict = {"datetime": datetime.fromtimestamp(f["dt"], tz=timezone.utc).isoformat()}
                    fdict.update(f["components"])
                    fdict.update(f["main"])
                    self._extra_state_attributes["forecast"].append(fdict)

        except ValueError:
            self._state = None
