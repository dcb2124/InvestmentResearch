# -*- coding: utf-8 -*-
"""
Created on Wed Jun  9 13:20:47 2021

@author: David Billingsley
"""
import valuation
import pandas as pd


stocks_df = pd.read_csv(
    'C:/Users/David Billingsley/InvestmentResearch/SLX etf holdings.csv')

valuations = [valuation.evaluate(ticker).out_all() for ticker in\
              stocks_df['Ticker'].apply(lambda x: x[:-3])]

valuations_df = pd.concat(valuations)


def str_out(valuations):
    output=''
    for key in valuations.keys():
        
        output = output + str(valuations[key]) 
        output = output +  '\n---------\n'
        
    return output
    

