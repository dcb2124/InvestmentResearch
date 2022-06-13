# -*- coding: utf-8 -*-
"""
Created on Thu May 27 23:28:46 2021

@author: David Billingsley
"""

import mechanize
from bs4 import BeautifulSoup
import numpy as np
from selenium import webdriver
import warnings
from time import sleep
from datetime import date
from valuation_utils import *
from test_utils import *

import tqdm
import re
import pandas as pd


class Equity():
    '''
    Class representing an equity valuation. Contains methods to scrape
    financial data from websites and set valuation under three different 
    methods based on (1) Price/Earnings Ratio, (2) Discount Cash Flow, and (3) 
    Return on Equity, for a given ticker.
    '''
    
    MARGIN_OF_SAFETY = 0.15
    DISCOUNT_RATE = 0.08
    GROWTH_DECAY_RATE = 0.05
    Y10_MULTIPLIER = 12
    PARSER = 'html.parser'
   
    def __init__(self, ticker):
        self.ticker = ticker.upper()
        self.data_lookups = [
            'EPS',
            'Median Historical PE',
            'Growth Rate',
            'Cash and Equivalents',
            'Total Liabilities',
            'Free Cash Flow',
            'Shares Outstanding',
            'Shareholder\'s Equity',
            'Return on Equity 5-yr',
            'Dividend per share'
            ]
        
        self.data = {}
        self.valuation = {}
        self.raw_data = {}
        self.quote = {}
        self.date = date.today()
        self.value_returns = {}
             
    def __str__(self):
        '''
        Returns
        -------
        final : str
            String representation of ticker, its valuations, and associated 
            financial data.

        '''
        
        colon_ = ': '
        
        tickerline = self.ticker + '\n'
        quoteline = 'QUOTE' + '\n'
        priceline = 'Price as of ' + str(self.quote['Date']) + colon_ + self.dollar_format(self.quote['Price']) + '\n'
        valuationline = 'VALUATION' + '\n'
        
        valuationblock = ''
        for key in self.valuation.keys():
            valuationblock += key + colon_ + self.dollar_format(self.valuation[key]) + '\n'
        valuationblock += '\n'
        
        valuereturnsline = 'VALUE RETURNS ' + '\n'
        
        valuereturnsblock = ''
        for key in self.value_returns.keys():
            valuereturnsblock += key + colon_ + self.percent_format(self.value_returns[key]) + '\n'
        valuereturnsblock += '\n'
        
        dataline = 'DATA' + '\n'
        
        eps = 'EPS: ' + str(self.data['EPS']) + '\n'
        gr = 'Growth Rate: ' + self.percent_format(self.data['Growth Rate']) + '\n'
        mhp = 'Median Historical P/E: ' + str(self.data['Median Historical P/E']) + '\n'
        cash = 'Cash and Cash Equivalents: $' + self.thousands_format(self.data['Cash and Cash Equivalents']) + '\n'
        tl = 'Total Liabilities: $' + self.thousands_format(self.data['Total Liabilities']) + '\n'
        fcf = 'Free Cash Flow: $' + self.thousands_format(self.data['Free Cash Flow']) + '\n'
        sh = 'Shares Oustanding: ' + self.thousands_format(self.data['Shares Outstanding'])+ '\n'
        sheq = 'Shareholders\' Equity' + self.thousands_format(self.data['Shareholders Equity']) + '\n'
        if 'Dividend Per Share' in self.data.keys():
            div = 'Dividend Per Share: ' + self.dollar_format(self.data['Dividend Per Share']) + '\n'
        roe = 'Return on Equity 5-yr: ' + self.percent_format(self.data['Return on Equity 5-yr'])+ '\n'
        
        quoteblock = quoteline + priceline + '\n'
        valuationblock = valuationline + valuationblock
        valuereturnsblock = valuereturnsline + valuereturnsblock
        datablock = dataline
        
        datapoints = [eps, gr, mhp, cash, tl, fcf, sh, sheq, roe]
        if 'Dividend Per Share' in self.data.keys():
            datapoints.append(div)
        
        for point in datapoints:
            datablock += point

        final= tickerline + quoteblock + valuationblock + valuereturnsblock + datablock
        
        return final
    
    def out_all(self):
        '''
        Get all data as a pandas df.

        Returns
        -------
        DataFrame
           All financial data associated with the equity as a dataframe

        '''
        
        all_data = {**self.quote, **self.valuation, **self.value_returns, **self.data}
        #reorder the columns
        columns = ['Price', 'Date', 'P/E Valuation', 'DCF Valuation', 'ROE Valuation', 
                   'P/E Value Return', 'DCF Value Return', 'ROE Value Return', 
                   'EPS', 'Growth Rate', 'Median Historical P/E', 'Cash and Cash Equivalents',
                   'Total Liabilities', 'Free Cash Flow', 'Shares Outstanding', 'Dividend Per Share',
                   'Return on Equity 5-yr']
        
        return pd.DataFrame(all_data, index=[self.ticker]).reindex(columns=columns)
        


    def set_data(self):
        '''
        Pull data from Morningstar and Yahoo Finance to fill in financial data
        associated with equity.

        Returns
        -------
        None.

        '''
        print('evaluating ' + self.ticker)        
        
        #Use mechanize and BeautifulSoup to parse YahooFinance pages for data
        mech = mechanize.Browser()
        
        #Get EPS TTM
        print('getting EPS TTM')
        try:
            self.eps_str = soup_(mech, url_yahoo(self.ticker)).find(attrs={'data-test' : 'EPS_RATIO-value'}).contents[0].text
        except AttributeError:
            print('Could not find EPS at ' + url_yahoo(self.ticker) + '. Maybe a bad url or non-existent stock?')
            self.eps_str = 0
        except Exception as e:
            print(e)
            self.eps_str=0
        
        float_convert_set(self, 'EPS', self.eps_str)    
        
        #get price
        print('getting current price')
        try:
            price = soup_(mech, url_yahoo(self.ticker))\
                .find(class_="Trsdu(0.3s) Fw(b) Fz(36px) Mb(-4px) D(ib)").text
        except Exception as e:
            price = 0
        self.quote['Price'] = float_convert(price)
        self.quote['Date'] = date.today()
        
        #get Projected Growth Rate
        print('getting growth rate') 
        try:
            growth_rate_str = soup_(mech, 
                                    url_yahoo(self.ticker, page = '/analysis?p='))\
                .find('span', text = 'Next 5 Years (per annum)').parent.\
                    next_sibling.text.strip('%')
            float_convert_set(self,'Growth Rate', growth_rate_str, factor = 0.01)
        except:
            print('could not get growth rate')
            self.data['Growth Rate'] = np.nan
        
        #calculate median historical p/e
        attrs = {'abbr':'Price/Earnings for ' + self.ticker}
        
        #open a headless selenium driver, load historical pe ratios, and 
        #make BeautifulSoup object to parse
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        driver = webdriver.Chrome(options = options)

        #driver should wait 10 seconds to try and load data.
        driver.implicitly_wait(10)
        
        driver.get(url_morningstar(self.ticker, 'valuation/price-ratio.html?t='))
        
        try:
            #see if the price_earnings tab is there and click on it,
            #or timeout after 10 secs
            print('getting historical p/e ratio')
            element = driver.find_element_by_id('price_earnings')
            element.click()
            sleep(5)
            
            pe_soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            pe_ratio_strs = [child.text for child in pe_soup.find(attrs=attrs).parent.children if getattr(child, 'name', None) == 'td']
            print(pe_ratio_strs)
            #don't include last value as it is TTM
            pe_ratio_strs_no_ttm = pe_ratio_strs[:-1]
    
            pe_ratios = [check_float(num) for num in pe_ratio_strs_no_ttm if check_float(num)]
            #last 5 non-empty values.
            median_hist_pe_5yr = np.median(pe_ratios[-5:]) if len(pe_ratios) >= 5 else np.median(pe_ratios)
        
            self.data['Median Historical P/E'] = median_hist_pe_5yr
            
        except Exception as e:
            print("An error ocurred getting median historical P/E")
            print(e)
            self.data['Median Historical P/E'] = np.nan
            
        
        #cash and cash equivalents
        print('loading balance sheet at ' + url_morningstar('balance-sheet/bs.html?t='))
        driver.get(url_morningstar(self.ticker, 'balance-sheet/bs.html?t='))
        
        #change to quarterly and wait 5 seconds for page to update.
        print('updating page to quarterly')
        script = 'javascript:SRT_stocFund.ChangeFreq(3,\'Quarterly\');'
        driver.execute_script(script)
        sleep(5)
        
        #-- For the following valuues, each try block tries to make sure 
        #selenium has loaded the data first, as sometimes it does not load.
        
        #get cash and cash equiv.
        print('getting cash and cash equivalents')
        try:     
            element = driver.find_element_by_id('data_i1')
            balance_soup = BeautifulSoup(driver.page_source, 'html.parser')
            cash_str = balance_soup.find(id='data_i1').find(id='Y_5')['rawvalue']
            print(cash_str)
            if check_float(cash_str):
                self.data['Cash and Cash Equivalents'] = check_float(cash_str)
        except Exception as e:
            print(e)
            self.data['Cash and Cash Equivalents'] = np.nan
            
        #total liabilities
        try:
            print('getting total liabilities')
            element = driver.find_element_by_id('data_ttg5')
            total_liabilities_str = balance_soup.find(id='data_ttg5').find(id='Y_5')['rawvalue']
            print(total_liabilities_str)
            if check_float(total_liabilities_str):
                self.data['Total Liabilities'] = check_float(total_liabilities_str)
        except Exception as e:
            print(e)
            self.data['Total Liabilities'] = np.nan
            
        #shareholders' equity
        try:
            print('getting shareholders equity')
            element = driver.find_element_by_id('data_ttg8')
            shareholders_equity_str = balance_soup.find(id='data_ttg8').find(id='Y_5')['rawvalue']
            print(shareholders_equity_str)
            if check_float(shareholders_equity_str):
                self.data['Shareholders Equity'] = check_float(shareholders_equity_str)
        except Exception as e:
            print(e)
            self.data['Shareholders Equity'] = np.nan
            
        #free cash flow
        try:
            print('getting free cash flow')
            driver.get(url_morningstar(self.ticker, 'ratios/r.html?t='))
            driver.find_element_by_id('i11')
            ratio_soup = BeautifulSoup(driver.page_source,'html.parser')
            free_cash_flow_str = ratio_soup.find(id='i11').parent.find('td', attrs={'headers' : 'Y10 i11'}).text.replace(',', '')
            print(free_cash_flow_str)
            if check_float(free_cash_flow_str):
                self.data['Free Cash Flow'] = float_convert(free_cash_flow_str, 1e6)
        except Exception as e:
            print(e)
            self.data['Free Cash Flow'] = np.nan
            
        #shares outstanding
        try:
            print('getting shares outstanding')
            driver.find_element_by_id('i7')
            shares_outstanding_str = ratio_soup.find(id='i7').parent.find('td', attrs={'headers' : 'Y10 i7'}).text.replace(',', '')
            print(shares_outstanding_str)
            if check_float(shares_outstanding_str):
                self.data['Shares Outstanding'] = float_convert(shares_outstanding_str, 1e6)
        except Exception as e:
            print(e)
            self.data['Shares Outstanding'] = np.nan
            
        #dividend
        try:
            print('getting dividend per share')
            driver.find_element_by_id('i6')
            dividend_str = ratio_soup.find(id='i6').parent.find('td', attrs={'headers' : 'Y10 i6'}).text.replace(',', '')
            print(dividend_str)
            if check_float(dividend_str):
                self.data['Dividend Per Share'] = float_convert(dividend_str)
            else: 
                self.data['Dividend Per Share'] = np.nan
        except Exception as e:
            print(e)
            self.data['Dividend Per Share'] = np.nan
            
        #return on equity
        print('getting return on equity')
        try:
            driver.get(url_morningstar(self.ticker, 'ratios/r.html?t=')+'#tab-profitability')
            roe_row = ratio_soup.find(id='i26').parent.children
            roe_historical = [float_convert(child.text, 1e-2) for child in roe_row if (getattr(child, 'name', None) == 'td' and check_float(child.text))]
            print(roe_historical)
            #-6 to -2 because -1 is TTM
            self.data['Return on Equity 5-yr'] = np.average(roe_historical[-6:-2])
        except Exception as e:
            print(e)
            self.data['Return on Equity 5-yr'] = np.nan

        driver.quit()
        return self.data
    
    def value(self, method, margin_of_safety=MARGIN_OF_SAFETY, 
               discount_rate=DISCOUNT_RATE, growth_decline = GROWTH_DECAY_RATE, 
               year_10_multiplier = Y10_MULTIPLIER):
        '''
        Values the equity based on the desired method price/earnings ratio.

        Parameters
        ----------
        method : string
            The valuation method. Must be one of {'pe', 'dcf', 'roe'}
        margin_of_safety : float, optional
            Margin of safety needed for your investment strategy. 
            The default is MARGIN_OF_SAFETY = 0.15.
        discount_rate : float, optional
            The discount rate over the investment period. 
            The default is DISCOUNT_RATE = 0.08.
        growth_decline : float, optional
            The rate of decay in growth of the company. 
            The default is GROWTH_DECAY_RATE = 0.05.
        year_10_multiplier : float, optional
            DESCRIPTION. The default is Y10_MULTIPLIER = 12.

        Returns
        -------
        value_ : float
            The value of the equity.

        '''
        assert method in ['pe', 'dcf', 'roe'], 'Method must be one of {\'pe\', \'dcf\', \'roe\'}'
        
        if method == 'pe':
            
            safe_growth_rate = self.data['Growth Rate'] * (1.0 - margin_of_safety)
            eps = self.data['EPS']
            pe = self.data['Median Historical P/E']
            
            if eps < 0:
                warnings.warn('EPS is negative. P/E valuation is not useful.')            
            
            value_series = [eps * (1 + safe_growth_rate)**t for t in range(6)]
            five_year_value = value_series[-1] * pe
            value_ = five_year_value / (1+discount_rate)**5
            
            #update valuation
            self.valuation['P/E Valuation'] = value_
        
        if method == 'dcf':
            
            fcf = self.data['Free Cash Flow']
            cash = self.data['Cash and Cash Equivalents']
            liabilities = self.data['Total Liabilities']
            shares = self.data['Shares Outstanding']
            
            safe_growth_rate = self.data['Growth Rate'] * (1.0 - margin_of_safety)
            
            fcf_x_growth_series = [fcf]
            
            growth_series = [1+((safe_growth_rate) * (1-growth_decline)**t) for t in range(0,10)]
            
            for i in range(0,10):
                fcf_x_growth_series.append(fcf_x_growth_series[-1] * growth_series[i])
            
            fcf_x_growth_series = fcf_x_growth_series[1:]       
                
            npv_fcf_series = [x / (1+discount_rate)**t for x,t in zip (fcf_x_growth_series, range(1,11))]
            
            total_npv_fcf = np.sum(npv_fcf_series)
            year_10_fcf_value = npv_fcf_series[-1] * year_10_multiplier 
            
            company_value = total_npv_fcf + year_10_fcf_value + cash - liabilities
            value_ = company_value/shares
            
            #update valuation
            self.valuation['DCF Valuation'] = value_
            
        if method == 'roe':
            
            safe_growth_rate = self.safe_growth(self.data['Growth Rate'])
            shs_eq = self.data['Shareholders Equity']
            roe = self.data['Return on Equity 5-yr']
            sh_out = self.data['Shares Outstanding']
            div = self.data['Dividend Per Share']
            
            eq = shs_eq/sh_out
            
            eq_series = [eq * (1+safe_growth_rate)**t for t in range(1,11)]
            div_series = [div * (1+safe_growth_rate)**t for t in range(1,11)]
            
            npv_div_series= [ div / ((1+discount_rate)**t) for div,t in zip(div_series, range(10))]
            
            y10_net_income = eq_series[-1] * roe
            required_value = y10_net_income/discount_rate
            
            npv_required_value = required_value/((1+discount_rate)**10)
            
            npv_dividends= np.sum(npv_div_series)
            
            value_ = npv_required_value + npv_dividends
            
            self.valuation['ROE Valuation'] = value_
                    
        return value_
    
    def safe_growth(self, growth, margin_of_safety = MARGIN_OF_SAFETY):
        
        return growth * (1 - margin_of_safety)
    
    def update_date(self):
        
        today = date.today()
        self.date = today()
        
        return today
    
    def quote(self):
        
        #this doesn't do anything yet
        
        return self.quote
    
    def value_return(self, price, value):
        
        #tells what the return would be if the price converged to the value.
        
        return (value - price)/price
    
    def get_value_returns(self):

        
        price = self.quote['Price']
        value_return = self.value_return
        
        for key in self.valuation.keys():
            value = self.valuation[key]
            returns_key = key[:3] + ' Value Return'
            self.value_returns[returns_key] = value_return(price, value)
       
        '''    
        pe = self.valuation['P/E Valuation']
        dcf = self.valuation['DCF Valuation']
        roe = self.valuation['ROE Valuation']
        
        
        
        self.value_returns['P/E Value Return (%)'] = value_return(price, pe)
        self.value_returns['DCF Value Return (%)'] = value_return(price, dcf)
        self.value_returns['ROE Value Return (%)'] = value_return(price, roe)
        '''        
        return self.value_returns
    
    def get_all(self):
    
        return self.quote, self.valuation, self.value_returns, self.data
    
    def all_value(self):
        
        for method in {'pe', 'dcf', 'roe'}:
            self.value(method)
        
        return self.valuation
    
    
        
        
       

#TODO: How to handle None types for example for EPS - if EPS is negative. 
#Yahoo v. morningstar data. There appear to be slight differences.
#Move functions outside of class defintion?
#convert variables to self. 
#let you edit data directly.
#how to handle "-" in morningstar data pe retrieval
#move data setting functions outside of set_data so they can be retried if they fail.
#add fields for raw series data.
#sometiems companies don't report cash and cash equivalents?? 
#a show data functoin to make this more readable.
#PIOTROSKI F-SCORE
#ALTMAN Z
#BENEISH M-score
#get price.
#add option to make it not headless, for debugging purposes
#data reactid50
#kwargs for valuation.
#make a __str__ function
#make Nas for empty values.
#turn functions like float_convert and dollar form into helper fuctions in their own package

def evaluate(ticker):
    
    stock = Equity(ticker)
    
    stock.set_data()

    try:
        stock.value(method='pe')
    except:
        print('Could not complete PE valuation')
    
    try:
        stock.value(method='dcf')
    except:
        print('Could not complete DCF valuation')
        
    try:
        stock.value(method='roe')
    except:
        print('Could not complete ROE valuation')
        
    try:
        stock.get_value_returns()
    except:
        print('Could not get value returns.')
        
    return stock

def evaluate_tickers(tickers):
    
    valuations = [evaluate(ticker).out_all() for ticker in tickers]
        
    return pd.concat(valuations)

