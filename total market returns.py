# -*- coding: utf-8 -*-
"""
Created on Thu May 13 16:53:48 2021

@author: David Billingsley
"""

'''
Gets the total market returns since 1999-01-01. Just for observational purposes.

'''
import pandas as pd


def read_in(filename):
    
    out = pd.read_csv(filename, parse_dates=['Date']).set_index('Date')
    
    return out.dropna()

def set_ret(df, days):
    
    colname = str(days) + '-Day Return'
    
    df[colname] = (df['Adj Close'] - df['Adj Close'].shift(days)) / df['Adj Close'].shift(252)
    
    return df



nyse = read_in('C:/Users/David Billingsley/InvestmentResearch/NYSE Composite.csv')
nasdaq = read_in('C:/Users/David Billingsley/InvestmentResearch/Nasdaq Composite.csv')

set_ret(nyse, 252)
set_ret(nasdaq, 252)

nyse_post99 = nyse.loc['1999-01-01' : ].copy()
nasdaq_post99 = nasdaq.loc[ '1999-01-01' : ].copy()
