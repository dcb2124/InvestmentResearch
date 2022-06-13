# -*- coding: utf-8 -*-
"""
Created on Sun Mar  6 17:47:38 2022

@author: User
"""

import yfinance as yf

def describe(ticker):
    t = yf.Ticker(ticker)
    return t.info['longBusinessSummary']