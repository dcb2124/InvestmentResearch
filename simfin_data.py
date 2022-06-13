# -*- coding: utf-8 -*-
"""
Created on Thu May 20 18:08:20 2021

@author: David Billingsley
"""

'''
This uses altman-z score and PCA to analyze bankruptcy risk across the market
based on financial statement data.
'''


import simfin as sf
from simfin.names import *
import pandas as pd
import numpy as np
import seaborn as sns
import random
from scipy import stats
from sklearn import linear_model
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
import matplotlib.pyplot as plt
from datetime import date, timedelta

sf.set_data_dir('C:/Users/David Billingsley/InvestmentResearch/simfin_api_data')
sf.set_api_key(api_key='free')

#hub parameters
days = 90
market='us'
offset = pd.DateOffset(days=days)
refresh_days = 30
refresh_days_shareprices = 1

#Get some random sample tickers, for testing purposes
df_companies = sf.load_companies(index=TICKER, market=market)
tickers_rand = random.choices(df_companies.index, k=5)

hub = sf.StockHub(market=market, offset=offset,
                  refresh_days=refresh_days,
                  refresh_days_shareprices=refresh_days_shareprices)


df_income = hub.load_income(variant = 'ttm')
df_balance = hub.load_balance(variant = 'ttm')
df_cashflow = hub.load_cashflow(variant = 'ttm')
df_prices = hub.load_shareprices(variant ='daily')
df_industries = sf.load_industries()
df_returns_1_3y = hub.mean_log_returns(name='Mean Log Return 1-3y',
                         future=True, annualized=True,
                         min_years=1, max_years=3)

def signals():
    '''
    Calculates standard simfin trading signals.

    Returns
    -------
    None.

    '''
    df_volume_signals = hub.volume_signals(window = 21)


def sample(df):
    '''
    Samples a dataframe based randomly pre-selected tickers.

    Parameters
    ----------
    df : DataFrame
        set of all tickers
        
    
    Returns
    -------
    TYPE
        randomly selected tickers

    '''
    
    return df.loc[tickers_rand]
    
def split_dates():
    '''
    Gives the date on which to split data set into training and validation.
    

    Returns
    -------
    val_start : datetime 
        start of validation set data
    test_start : datetime
        start of test set data

    '''
    
    today= date.today()
    split_period = timedelta(days = 365*3)
    
    test_start = pd.bdate_range(start = today - split_period, end = today)[0]
    
    val_start = pd.bdate_range(start = test_start - split_period, end = test_start)[0]
    
    return val_start, test_start
    
'''
I'm going to set the offset to 180 days.
Restatements appear to be coming either within 3 months, or at 1 year 
intervals. The 1 year intervals suggest that those are from revisions to 10-k 
filings, and the within 3 months are the 10-q. see histogram.
If we offset to 180 days, remove any lookahead bias from the 10-qs, and reduce 
the impact of the lookahead bias from the 10-ks because those will only be 1 
in 4 data points used to construct the TTM.   
'''


def daily_fin_data():
    '''
    Offset data by 6 months and re-index all data to daily.

    Returns
    -------
    df_income_daily : DataFrame
        daily income statement data
    df_balance_daily : DataFrame
        daily balance sheet data
    df_cashflow_daily : DataFrame
        daily cash flow statement data

    '''
    print("Building daily income data... ")
    df_income_daily = sf.reindex(df_src=df_income, df_target = df_prices, group_index = TICKER, method='ffill')
    print('Done!')
    print("Building daily balance sheet data... ")
    df_balance_daily = sf.reindex(df_src=df_balance, df_target = df_prices, group_index = TICKER, method='ffill')
    print('Done!')
    print("Building daily cash flow data... ")
    df_cashflow_daily = sf.reindex(df_src=df_cashflow, df_target = df_prices, group_index = TICKER, method='ffill')
    print('Done!')
    print('getting daily volume signals')
    
    return df_income_daily, df_balance_daily, df_cashflow_daily


def altman_z_test(rand=True):
    '''
    Calculate altman z-score for set of tickers.

    Parameters
    ----------
    rand : boolean, optional
        Whether to select random tickers for testing purposes. 
        The default is True.

    Returns
    -------
    df_az : DataFrame
        Altman Z-score for each equity and associated financial data.

    '''
    if rand:
        tickers = tickers_rand
    else:
        tickers = df_companies.index

        total_assets = df_balance_daily.loc[tickers, ['Total Assets']]
        total_current_assets = df_balance_daily.loc[tickers, ['Total Current Assets']]
        total_current_liabilities = df_balance_daily.loc[tickers, ['Total Current Liabilities']]
        retained_earnings = df_balance_daily.loc[tickers, ['Retained Earnings']]
        pretax_income = df_income_daily.loc[tickers, ['Pretax Income (Loss)']]
        interest_expense = df_income_daily.loc[tickers, ['Interest Expense, Net']]
        revenue  = df_income_daily.loc[tickers, ['Revenue']]
        mcap = df_volume_signals.loc[tickers, ['Volume Market-Cap']]
        total_liabilities = df_balance_daily.loc[tickers, ['Total Liabilities']]
            
    
    df_az = pd.concat([ total_assets, 
                      total_current_assets, 
                      total_current_liabilities, 
                      retained_earnings,
                      pretax_income,
                      interest_expense,
                      revenue,
                      mcap,
                      total_liabilities], axis=1)
    
    
    df_az['X1'] = (df_az['Total Current Assets'] - df_az['Total Current Liabilities'])/df_az['Total Assets']
    df_az['X2'] = df_az['Retained Earnings']/df_az['Total Assets']
    df_az['X3'] = (df_az['Pretax Income (Loss)'] - df_az['Interest Expense, Net'])/df_az['Total Assets']
    df_az['X4'] = df_az['Volume Market-Cap']/df_az['Total Liabilities']
    df_az['X5'] = df_az['Revenue']/df_az['Total Assets']
    
    df_az['Altman Z'] = 1.2 * df_az['X1'] + 1.4 * df_az['X2'] + 3.3 *\
        df_az['X3'] + 0.6 * df_az['X4'] + 1.0 * df_az['X5']
    
    return df_az


def new_altman_z_coefs(rand=True):
    clf = linear_model.LinearRegression(fit_intercept=True)
    x = altman_z_test(rand=rand)
    #get rid of infs and nans
    x.replace([np.inf, -np.inf], np.nan, inplace=True)
    x.dropna(inplace=True)
    if rand:
        y = df_returns_1_3y.loc[tickers_rand].fillna(0)
    else:
        y = df_returns_1_3y.fillna(0)
    y_ = sf.reindex(df_src = y, df_target = x, group_index=TICKER, method='ffill')
    reg = clf.fit(x, y_)
    return reg, x, y_

def pca_analysis(x, n = 2):
    '''
    StandardScales data and fits a PCA object to it.

    Parameters
    ----------
    x : data
        the data to fit PCA to
    n : int, optional
        the number of principal components desired in the PCA fit

    Returns
    -------
    pca : PCA
        the fitted PCA object
    x_ : numpy array
        StandardScaler transformed data

    '''
 
    
    pca = PCA(n_components = n)
    
    x_ = StandardScaler().fit_transform(x)
    
    pca.fit(x_)
    return pca, x_


def biplot(score, coeff, labels=None, k=20000, **kwargs):
    '''
    Create a biplot of the PCA analysis to find orthongonality.
    '''
    
    fontsize=kwargs['fontsize'] if 'fontsize' in kwargs.keys() else 'medium'
    fontcolor =kwargs['fontcolor'] if 'fontcolor' in kwargs.keys else 'blue'
    
    
    random_indices = np.random.choice(len(score), size=k, replace=False )
    
    score = score[random_indices, :]
    
    xs = score[:,0]
    ys = score[:,1]
    n = coeff.shape[0]
    scalex = 1.0/(xs.max() - xs.min())
    scaley = 1.0/(ys.max() - ys.min())
    plt.figure(dpi=1200)
    plt.scatter(xs * scalex,ys * scaley, s=5)
    for i in range(n):
        plt.arrow(0, 0, coeff[i,0], coeff[i,1],color = 'r',alpha = 0.5)
        if labels is None:
            plt.text(coeff[i,0]* 1.15, coeff[i,1] * 1.15, "Var"+str(i+1), color = 'g', ha = 'center', va = 'center', fontsize=fontsize)
        else:
            plt.text(coeff[i,0]* 1.15, coeff[i,1] * 1.15, labels[i], color = 'g', ha = 'center', va = 'center', fontsize=fontsize)
    plt.xlim(-1,1)
    plt.ylim(-1,1)
    plt.xlabel("PC{}".format(1))
    plt.ylabel("PC{}".format(2))
    plt.grid()
    
def call_biplot(score, components, k=20000, labels=None, **kwargs):
    
    biplot(score[:,0:2], np.transpose(components[0:2, :]), k=k, labels = labels, **kwargs)

altman_factors = ['Total Assets', 'Total Current Assets', 'Total Current Liabilities',
                  'Retained Earnings', 'Pretax Income (Loss)', 'Interest Expense, Net',
                  'Revenue', 'Volume Market-Cap', 'Total Liabilities' ]
#to get x do new altman_z_coeffs, then pca_analysis, then feed x_ into biploth


#How to handle NaNs in signals? I guess you could just .fillna(method = 'ffill')
#Also I need to look at PCA analysis again and see how it works. 


#Questions to Ask
'''
Should evaluate each of these by sector.
1. Which Valuation Metrics do the most explanation of returns over a given 
period? We can use PCA to figure this out, or we can also use a decision tree.

2. Value investing is based on the idea that the market is inefficient in the 
short term, but efficient in the long term. So how long before the market 
becomes efficient? Compare DCF, PE, and ROE methods, GuruFocus, Y-Charts, and 
what's available on GuruFocus - Y-Chart. You could also create efficiency
confidency intervals. So, you say, I am 50% confident the sector will become
efficient within 32-48 months. 80% confident in 20 to 60 months, etc. 

3. What is an appropriate margin of safety - BE CAREFUL to form a hypothesis
about what it is, and then evaluate it. Don't use the data to tell you what
and appropriate margin of safety is.

4. How well do certain predictors like Piotroski F-score (Financial Strength)
 Altman Z-score (bankruptcy likelihood), and Beneish M-Score (manipulation) 
 whether a company is likely to fail within a given time period? Maybe these
 could tell you whether to short. 
'''
### - UNUSED FUNCTIONS I MAY BUT PROBABLY WILL NOT WANT TO REUSE ###
def val_signals():

    df_val_signals = sf.val_signals(df_income_ttm=df_income,
                                    df_balance_ttm=df_balance,
                                    df_cashflow_ttm=df_cashflow,
                                    df_prices=df_prices, fill_method='ffill'
                                    )
    
#Add date offset in financial data to remove lookahead bias from restatements.
def offset_report_date(df, days):
    
    return sf.add_date_offset(df=df,
                              date_index=REPORT_DATE,
                              offset=pd.DateOffset(days=days))