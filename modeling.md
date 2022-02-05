## Observation

- Largest deviations seem to come from the feature not being home (top 15 largest ratio is because we are not home).
- Is there an effect on sun heating the roof starting from April? (e.g: 29 April 2021). What about having a feature for month of the year?
- There might be some anomalies (e.g: boiler runs without heating the home). We should investigate dates where the boiler does not run and energy consumption is high (e.g: 31/10/2020).
- Is there an effect of weekdays vs weekends?
- Aggregation of the mean has the lowest RMSE
- Model falls short in low temperatures or high temperature
- Prediction can be negative which we can easily fix
- The boiler can also run to heat at the min temperature set (often 15). See 29/12/2020 where we are away but the boiler heats to keep the home around 15.
- We should export CI in prediction see - https://stackoverflow.com/questions/17559408/confidence-and-prediction-intervals-with-statsmodels

## Literature

- This [paper](https://www.researchgate.net/publication/336747306_Heating_demand_and_indoor_air_temperature_prediction_in_a_residential_building_using_physical_and_statistical_models_a_comparative_study) predicts energy consumption and temperature in a residential building. They use both a physical model as well a statistical model.

Learnings:

- They use day of the week and time of day as a feature. Could we use a similar approach?
- Learn one month of data and predict on the next one.
- The statistical model shows high variance in error. Possibly due to poor data quality.
