# InvestmentResearch
Some tools I created conduct research on equity markets.

## Valuation
Valuation automatically scrapes financial data from Yahoo Finance and Morningstar to conduct valuation based on price/earnings ratio, discount cash flow, and return on equity. It can do this for any basket of stocks. Results can be seen in the results folder. Inputs are under the data folder.

## simfin_data
This uses altman-z score and PCA to analyze bankruptcy risk across the market
based on financial statement data.

## Dependecies
Pandas is required for everything. You'll also need simfin for the simfin_data script. Otherwise it relies only on standard libraries.
