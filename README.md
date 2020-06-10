## Compans Data

Feel free to reach out to me on Twitter to discuss: [martindaniel4](https://twitter.com/martindaniel4).

### Background

In July 2018 my wife and I bought and revamp a home in Paris, France. The name of the street is 'Compans' so I named that repo 'Compans Data'. We love our place but one issue we have is the level of heat we experience. Since our flat has a single-glass ceiling (or "Verrière") the sun hits pretty hard and the prospect of extreme heat waves happening in Paris is worrysome.

In February 2019, I acquired a Netatmo thermostat (see -  https://www.netatmo.com/fr-fr/energy/thermostat) that I connected to my heating system. In addition to remote control of my home temperature, it also collects temperature. Since Netatmo has an API I figured I would give it a try. 

_A picture of my Netatmo thermostat in my apartment_

<img src='img/thermostat.jpg' width='300'> </img>

Here is for instance a first graph of those temperature, since I have installed my thermostat: 

_Interior temperature graph in my home since Feb. 2019 (step = 30min, celsius)_

<img src='img/temperature.png' width='300'> </img>

### How to use it? 

The main logic is coded in Python in `netatmo_temperature.py`. You can also check `netatmo_thermostat.ipynb` where I run some analysis in an ipython notebook.

- First create an app on Netatmo platform (see https://dev.netatmo.com/)
- Then add to your path the following variables: client_id, client_secret, email and password. 
- Install Python libraries with `pip install -r requirements.txt`
- You can now retrieve all your temperature with the following command: 

```
from netatmo_temperature import * 
pull_temperature()
```

### Next Steps

My main goal is to retrieve measures of interior temperature on a long timeframe. My hope is that I can start running some analysis and inform some home decisions as I revamp my home. For instance: 

- What's the impact of covering my ceiling from the interior? 
- What's the impact of sun or cloud on interior temperature? 
- How much temperature do I save if I change for a double glass-ceiling? 

Building on that, I also want to incorporate additional measures such as electricity consumption, hygrometry and more! 
  