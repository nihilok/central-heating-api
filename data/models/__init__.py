"""
// EXAMPLE persistence.json:
{
  "systems": [
    {
      "relay": {
        "url_on": "http://192.168.1.1/off?pin=2",
        "url_off": "http://192.168.1.1/on?pin=2",
        "url_status": "http://192.168.1.1/status?pin=2",
        "cached_value": false,
        "last_updated": 1711959819.9228377,
        "URLS": {
          "on": "http://192.168.1.1/off?pin=2",
          "off": "http://192.168.1.1/on?pin=2"
        }
      },
      "sensor": {
        "url": "http://192.168.1.209",
        "adjustment": 2.0,
        "cached_value": 21.1,
        "last_updated": 1710486480.7541046
      },
      "system_id": "upstairs",
      "program": true,
      "periods": [
        {
          "start": 7.0,
          "end": 20.0,
          "target": 21.0,
          "days": {
            "monday": false,
            "tuesday": false,
            "wednesday": false,
            "thursday": false,
            "friday": false,
            "saturday": true,
            "sunday": true
          },
          "id": "b156691a-5a54-469b-81fd-e949b6eb415d"
        },
        {
          "start": 7.0,
          "end": 10.5,
          "target": 21.0,
          "days": {
            "monday": true,
            "tuesday": true,
            "wednesday": true,
            "thursday": true,
            "friday": true,
            "saturday": false,
            "sunday": false
          },
          "id": "99ad598b-2f90-4710-940f-4413e834d876"
        },
        {
          "start": 15.5,
          "end": 20.5,
          "target": 21.0,
          "days": {
            "monday": true,
            "tuesday": true,
            "wednesday": true,
            "thursday": true,
            "friday": true,
            "saturday": false,
            "sunday": false
          },
          "id": "be716865-b60c-4292-b0e0-58c47d651e09"
        }
      ],
      "advance": null,
      "boost": null,
      "temperature": 21.5,
      "temperature_expiry": null
    },
    {
      "relay": {
        "url_on": "http://192.168.1.1/off?pin=1",
        "url_off": "http://192.168.1.1/on?pin=1",
        "url_status": "http://192.168.1.1/status?pin=1",
        "cached_value": false,
        "last_updated": 1711962106.450653,
        "URLS": {
          "on": "http://192.168.1.1/off?pin=1",
          "off": "http://192.168.1.1/on?pin=1"
        }
      },
      "sensor": {
        "url": "http://192.168.1.44",
        "adjustment": 1.0,
        "cached_value": 21.5,
        "last_updated": 1711959811.0714488
      },
      "system_id": "downstairs",
      "program": true,
      "periods": [
        {
          "start": 6.833333333333333,
          "end": 10.5,
          "target": 21.0,
          "days": {
            "monday": true,
            "tuesday": true,
            "wednesday": true,
            "thursday": true,
            "friday": true,
            "saturday": false,
            "sunday": false
          },
          "id": "920e5942-41fd-4cc4-98af-1f236d35143c"
        },
        {
          "start": 7.0,
          "end": 10.5,
          "target": 21.0,
          "days": {
            "monday": false,
            "tuesday": false,
            "wednesday": false,
            "thursday": false,
            "friday": false,
            "saturday": true,
            "sunday": true
          },
          "id": "53221a47-c823-4edd-83b5-272655e2870a"
        },
        {
          "start": 10.5,
          "end": 16.0,
          "target": 20.0,
          "days": {
            "monday": false,
            "tuesday": false,
            "wednesday": false,
            "thursday": false,
            "friday": false,
            "saturday": true,
            "sunday": true
          },
          "id": "cdee0b55-9cba-4ecf-b4f9-6da9590d67f1"
        },
        {
          "start": 15.5,
          "end": 21.5,
          "target": 21.0,
          "days": {
            "monday": true,
            "tuesday": true,
            "wednesday": true,
            "thursday": true,
            "friday": true,
            "saturday": false,
            "sunday": false
          },
          "id": "29e6b03a-a7fb-420c-9781-e5847a7a8fd0"
        },
        {
          "start": 16.0,
          "end": 21.5,
          "target": 21.0,
          "days": {
            "monday": false,
            "tuesday": false,
            "wednesday": false,
            "thursday": false,
            "friday": false,
            "saturday": true,
            "sunday": true
          },
          "id": "3f972d5b-11c7-4622-a2f7-cc9fda8334ca"
        }
      ],
      "advance": null,
      "boost": null,
      "temperature": null,
      "temperature_expiry": null
    }
  ]
}
"""