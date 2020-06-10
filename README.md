## Netatmo Temperature

The script presented here shows how to pull temperature data from Netatmo thermostat, see -

### Background

In July 2018 my wife and I bought and revamp a home in Paris, France. We love our place but one issue we had was the level of heat we experienced. Since our flat has a single-glass ceiling (or "Verrière"), the sun heats our living room. 

In February 2019, I acquired a Netatmo thermostat (see -  https://www.netatmo.com/fr-fr/energy/thermostat) that I connected to my heating system. In addition to remote control of my home temperature, it also collects temperature. Since Netatmo has an API I figured I would give it a try. 

_A picture of my Netatmo thermostat in my apartment_

<img src='img/thermostat.jpg' width='300'> </img>

The output of that repo is to retrieve measures of interior temperature on a long timeframe to start running some analysis. Here is for instance a graph, since I have installed my thermostat: 

_Interior temperature graph in my home since Feb. 2019 (step = 30min, celsius)_

<img src='img/temperature.jpg' width='300'> </img>

### How to use it? 