# -*- coding: utf-8 -*-
"""
Created on Thu Jun  9 11:38:59 2022

@author: User
"""

'''
Some utility functions for formatting strings.
'''
import numpy as np
import mechanize
from bs4 import BeautifulSoup

def dollar_format(amount):
    '''
    Turns a float into a dollar amount str. 
    Move to utils.

    Parameters
    ----------
    amount : float
        A dollar amount

    Returns
    -------
    str
        Dollar amount in $X.XX format.

    '''
    
    return '$' + "{:.2f}".format(amount)

def percent_format(amount):
    '''
    Turns a float into a % format string. 
    Move to utils.

    Parameters
    ----------
    amount : float
        A number

    Returns
    -------
    str
        Amount in XX.XX% format.

    '''
    
    return '{:.2%}'.format(amount)

def thousands_format(amount):
    '''
    Turns a float into a formatted string  with commas to denote 1000s factors.

    Parameters
    ----------
    amount : float
        DESCRIPTION.

    Returns
    -------
    TYPE
        XXX,XXX number format string.

    '''
    
    return '{:,}'.format(amount)

def url_yahoo(ticker, page=''):
    
    url_yahoo_quote = 'https://finance.yahoo.com/quote/' + ticker
    print(url_yahoo_quote)
    
    return url_yahoo_quote if page == '' else url_yahoo_quote + page + ticker


def url_morningstar(ticker, page):
    
    morningstar = 'https://financials.morningstar.com/'
    
    return morningstar + page + ticker

def float_convert_set(equity, key, value, factor=1.0):
    '''
    Tries to convert a string value into a factor multiplied value for a given 
    Equity then set that value in that Equity's financial data dictionary.
    Handles exceptions for when the data is for some reason missing after scrape.

    Parameters
    ----------
    equity : Equity object
        the Equity needing conversion of a value
    key : string
        the key in self.data.
    value : string
        value to be converted to a float
    factor : float, optional
        Multiply converted value by this factor. The default is 1.0.

    Returns
    -------
    None.

    '''
    
    try:
        equity.data[key] = float(value) * factor
    except ValueError:
        print('Retrieved ' + key + ' value ' + value + ' cannot be converted to float.')
        equity.data[key] = np.nan
    except TypeError as e:
        if value is None:             
            print('Retrieved None for ' + key + '.')
            equity.data[key] = np.nan
        else:
            print(e)
            equity.data[key] = np.nan
                    
def float_convert(value, factor=1.0):
    '''
    Converts a string value contained in financial data dict to a float, returns
    np.nan if it cannot be converted (e.g., no data was scraped)

    Parameters
    ----------
    value : string
        The value in the financial data dictionary as scraped.
    factor : TYPE, optional
        Factor to multiply by if desired. The default is 1.0.

    Returns
    -------
    float
        the converted value or np.nan

    '''
    
    if isinstance(value, str) and ',' in value:
        value = value.replace(',', '')
    
    try:
        return float(value) * factor
    except:
        print('Retrieved value ' + str(value) + 'cannot be converted to float.')
        return np.nan
    
def soup_(mech, url):
    '''
    Navigates to url and gives BeautifulSoup parse in return.

    Parameters
    ----------
    mech : mechanize Browser object
        
    url : string
        

    Returns
    -------
    BeautifulSoup object

    '''
    
    return BeautifulSoup(mech.open(url).read(), 'html.parser')


def check_float(string):
    '''
    Returns string as a float if possible, otherwise returns np.nan.

    Parameters
    ----------
    string : string
        DESCRIPTION.

    Returns
    -------
    float
        the string as float or np.nan if not possible.

    '''
    
    if ',' in string:
        string = string.replace(',', '')
        
    try:
        return float(string)
    except:
        print('Cannot convert ' + string + ' to float')
        return False