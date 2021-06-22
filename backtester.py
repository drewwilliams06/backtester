import pandas as pd
import numpy as np
import datetime
import matplotlib.pyplot as plt
import sys
import random




'''
Stores the amount of each asset held as a portfolio
Parameters:
  self.assets (dictionary, asset (str) : amount held (float)) - represents how much of each asset the portfolio holds
'''
class Portfolio:
    
    '''
    Initialize portfolio
    Parameters:
      assets (dictionary, asset (str) : amount held (float))
    '''
    def __init__(self, assets):
        self.assets=assets.copy()
        
    '''
    Remove some amount of an asset from the portfolio
    Parameters:
      asset (string in self.assets) - name of asset to be withdrawn
      amt (float>=0) - amount to withdraw
    Returns amount successfully withdrawn (not necessarily == amt)
    '''
    def withdraw(self, asset, amt):
        assert amt>=0, 'Cannot withdraw negative amt %s'%amt
        assert asset in self.assets, 'No such asset %s'%asset
        actualWithdrawal=min(self.assets[asset],amt)
        self.assets[asset]=max(0,self.assets[asset]-actualWithdrawal) #Ensure can't go negative
        return actualWithdrawal
    
    '''
    Add some amount of an asset to the portfolio
    Parameters:
      asset (string in self.assets) - name of asset to be deposited
      amt (float>=0) - amount to deposit
    '''
    def deposit(self, asset, amt):
        assert amt>=0, 'Cannot deposit negative amt %s'%amt
        assert asset in self.assets, 'No such asset %s'%asset
        self.assets[asset]=self.assets[asset]+amt
    
    '''
    Returns amount of asset in portfolio
    Parameters:
      asset (string in self.assets) - name of asset to check holdings of
    '''
    def getAsset(self, asset):
        assert asset in self.assets, 'No such asset %s'%asset
        return self.assets[asset]
    
    '''
    Returns a dictionary of holdings for given assets
    Parameters:
      assets (list(string in self.assets)) - names of assets to check holdings of
    '''
    def getAssets(self, assets):
        for asset in assets:
            assert asset in self.assets, 'No such asset %s'%asset
        return {k:self.assets[k] for k in assets}
    
    '''
    Returns a dictionary of holdings for all assets
    '''
    def getAllAssets(self):
        return self.assets.copy()
    
    '''
    Returns list of all asset names (list(string))
    '''
    def getAssetNames(self):
        return list(self.assets.keys())
    
    '''
    Calculates the value of each asset as converted to the target asset using an exchange rate dictionary.
    Parameters:
      target (string) - name of asset to convert other assets to (typically USD)
      exchangeToTarget (dict{asset:exchangeRate}) - mapping of assets to associated prices with respect to target (typically USD price)
    Returns: 
      values - a dictionary of each asset's corresponding value (asset:value)
      percentages - a dictionary of the percentage of the portfolio's value that is contributed by each asset (asset:percent) 
    '''
    def getValues(self,target,exchangeToTarget):
        assert target in self.assets, 'No such asset %s'%target
        values={asset:self.assets[asset]*exchangeToTarget[asset] for asset in self.assets}
        totalValue=sum(values.values())
        percentages={asset:values[asset]/totalValue for asset in self.assets}
        return values,percentages
    
    '''
    Returns the portfolio percentage makeup of a dictionary of portfolio values 
    Parameters:
      portfolioValues (dict{asset:value})
      totalValue (float) - total value of portfolio
    ''' 
    def getPercentages(portfolioValues,totalValue):
        return {asset:portfolioValues[asset]/totalValue for asset in self.assets}
        
        
'''
Intended to simulate an exchange for a market given historical data.

Parameters:
backData (DataFrame) - must include a datetime64 column, and a column for each asset with corresponding price
start (datetime64) - date to begin backtesting **must leave room between start of backdata and start of backtesting**
end (datetime64) - date to end backtesting
model (string) - name of investment model
portfolio (Portfolio) - initial holdings *this is where the asset names are derived from*

Return the portfolio value history with respect to time

TODO: 
Generalize model input
Allow multiple portfolio/model pairs to be run at once
models is a dict{name(str):model(fn)}
portfolios is a dict{name(str):portfolio(Portfolio)}
'''
def backtest(backData,start,end,models,portfolios):
    
    #get number of days from start to end
    days=(end-start)/np.timedelta64(1, 'D')
    
    #Get prices for all assets - currently this is specific to bitcoin and should be generalized. also ugly one liner
    priceBTC=float(np.array(backData.loc[backData['DateTime64']==start])[0][2].replace(',',''))
    #Use these prices to generate exchange rates to USD
    exchangeToTarget={'USD':1,'BTC':priceBTC}
    
    #track history of portfolio holdings and total value
    
    initialValues={}
    portfolioHistory=pd.DataFrame(columns=(['Day']+[(modelName + " Portfolio") for modelName in list(models.keys())]+[(modelName + " Value") for modelName in list(models.keys())]))
    for modelName in list(models.keys()):
        portfolio=portfolios[modelName]
        initialValues[modelName]=sum(portfolio.getValues('USD',exchangeToTarget)[0].values())
        

    
    #step one day
    for i in range(int(days)):
        
        #Get prices for all assets - currently this is specific to bitcoin and should be generalized. also ugly one liner
        priceBTC=float(np.array(backData.loc[backData['DateTime64']==start+i])[0][2].replace(',',''))
        #Use these prices to generate exchange rates to USD
        exchangeToTarget={'USD':1,'BTC':priceBTC}
        
        #Get value of portfolio in USD
        newRow={}
        for modelName in list(models.keys()):
            portfolioValues,portfolioPercentages=portfolios[modelName].getValues('USD',exchangeToTarget)
            totalValue=sum(portfolioValues.values())
            newRow[modelName+ " Portfolio"]=portfolios[modelName].getAllAssets()
            newRow[modelName+ " Value"]=totalValue
        newRow['Day']=start+i
        
            
            
        
        #Save day, portfolio, and USD value for current horizon in newRow, a dictionary mapping each
        #Currently ignores index. TODO: Make day the index instead of ignoring it?
        #newRow=portfolio.getAllAssets()
        #newRow['Day']=start+i
        #newRow['Total Value']=totalValue
        portfolioHistory=portfolioHistory.append(newRow,ignore_index=True)
        
        #Trim the backData to exclude the current day and beyond. 
        #This currently does not include open price, but maybe should. Need to decide time of day we make each decision.
        limitedData=backData.loc[backData["DateTime64"]<(start+i)]
        
        for modelName in list(models.keys()):
            model=models[modelName]
            portfolio=portfolios[modelName]
            #Get orders from model 
            orders=model(limitedData,portfolio,exchangeToTarget,initialValues[modelName],start,end,i)

            #Fill orders (currently assuming all orders can be filled at same price as open. Bad assumption)
            for order in orders:

                orderType=order[0]
                orderAsset=order[1]
                orderAmt=order[2]
                balanceUSD=portfolio.getAsset('USD')
                balanceAsset=portfolio.getAsset(orderAsset)

                if orderType=='B':
                    orderPrice=orderAmt*exchangeToTarget[orderAsset]
                    if balanceUSD>=orderPrice:
                        portfolio.withdraw('USD',orderPrice)
                        portfolio.deposit(orderAsset,orderAmt)
                    else:
                        if round(orderPrice-balanceUSD,8)==0: 
                            #Rounding error, no big deal
                            pass
                        else:
                            #Something probably went wrong, a model requested a bad trade
                            print("WARNING: Can't afford to buy %s %s for %s USD (USD balance %s)" %(orderAmt,orderAsset,orderPrice,balanceUSD))
                            print('Withdrawing %s USD to buy %s %s' %(balanceUSD,balanceUSD/exchangeToTarget[orderAsset],orderAsset))
                        portfolio.withdraw('USD',balanceUSD)
                        portfolio.deposit(orderAsset,balanceUSD/exchangeToTarget[orderAsset])

                elif orderType=='S':
                    orderPrice=orderAmt*exchangeToTarget[orderAsset]
                    if balanceAsset>=orderAmt:
                        portfolio.withdraw(orderAsset,orderAmt)
                        portfolio.deposit('USD',orderPrice)
                    else:
                        if round(orderAmt-balanceAsset,8)==0: 
                            #print("Seems to be rounding")
                            pass
                        else:
                            print('WARNING: Can\'t afford to sell %s %s for %s USD (%s balance %s)' %(orderAmt,orderAsset,orderPrice,orderAsset,balanceAsset))
                            print('Withdrawing %s %s for %s USD' %(balanceAsset,orderAsset,balanceAsset*exchangeToTarget[orderAsset]))
                        portfolio.withdraw(orderAsset,balanceAsset)
                        portfolio.deposit('USD',balanceAsset*exchangeToTarget[orderAsset])

                else:
                    print("Invalid order type.")
                
            
    portfolioHistory.index=portfolioHistory['Day']
    return portfolioHistory.drop('Day',axis=1)


##############################
#        Strategies
##############################

'''
Buy and hold strategy in which all USD is exchanged for BTC ASAP
'''
def HODL(limitedData,portfolio,exchangeToTarget,initialValue,start,end,i):
    amtUSD=portfolio.getAsset('USD')
    amtBTC=amtUSD/exchangeToTarget['BTC']
    return [['B','BTC',amtBTC]]


'''
Dollar Cost Average strategy
'''
def DCA(limitedData,portfolio,exchangeToTarget,initialValue,start,end,i):
    days=(end-start)/np.timedelta64(1, 'D')
    investmentPerDay=initialValue/(days)
    amtUSD=investmentPerDay
    amtBTC=amtUSD/(exchangeToTarget['BTC'])
    return [['B','BTC',amtBTC]]


'''
Generalized time series momentum strategy with lookback, rebalance
'''
def TSMOM(limitedData,portfolio,exchangeToTarget,initialValue,start,end,i,lookback,rebalance):
    yesterday=start+i-1
    #Get return since lookback months ago ago
    if (i-1)%rebalance!=0: #TODO: Not a specific date of week, could change, market could be closed, whatever
        return [] #no orders
    price_lookback=float(np.array(limitedData.loc[limitedData['DateTime64']==yesterday-lookback]['Price'])[0].replace(",",""))
    price_t=float(np.array(limitedData.loc[limitedData['DateTime64']==yesterday]['Price'])[0].replace(",",""))
    return_lookback=price_t-price_lookback
    if return_lookback>=0:
        amtUSD=portfolio.getAsset('USD') #Get all USD
        amtBTC=amtUSD/exchangeToTarget['BTC'] #Get amt btc we can buy with all USD
        return [['B','BTC',amtBTC]]
    else:
        amtBTC=portfolio.getAsset('BTC') #Get all BTC, sell it all
        #amtUSD=amtUSD/exchangeToTarget['BTC'] #Get amt btc we can buy with all USD
        return [['S','BTC',amtBTC]]


'''
return a function that the backtester can call
'''
def TSMOM_gen(lookback,rebalance):
    return lambda limitedData,portfolio,exchangeToTarget,initialValue,start,end,i : TSMOM(limitedData,portfolio,exchangeToTarget,initialValue,start,end,i,lookback,rebalance)

#Deprecated
'''
def TSMOM_D(limitedData,portfolio,exchangeToTarget,initialValue,start,end,i):
    yesterday=start+i-1
    assets=portfolio.getAllAssets()
    portfolio1=Portfolio({asset:assets[asset]/3 for asset in assets})
    portfolio2=Portfolio({asset:assets[asset]/3 for asset in assets})
    portfolio3=Portfolio({asset:assets[asset]/3 for asset in assets})
    orders1=TSMOM_gen(7,1)(limitedData,portfolio1,exchangeToTarget,initialValue,start,end,i)
    orders2=TSMOM_gen(30,1)(limitedData,portfolio2,exchangeToTarget,initialValue,start,end,i)
    orders3=TSMOM_gen(90,1)(limitedData,portfolio3,exchangeToTarget,initialValue,start,end,i)
    return orders1+orders2+orders3
'''

#params is a list of [(lookback,rebalance),(lookback,rebalance),...]
#returns a function for the backtester that equally weights portfolios of the given lookback,rebalance pairs
def TSMOM_diversify(params):
    n=len(params)
    TSMOM_list=[]
    for param in params:
        lookback=param[0]
        rebalance=param[1]
        #TSMOM_list+=[lambda limitedData,portfolio,exchangeToTarget,initialValue,start,end,i : TSMOM(limitedData,portfolio,exchangeToTarget,initialValue,start,end,i,lookback,rebalance)]
        TSMOM_list+=[TSMOM_gen(lookback,rebalance)]
    return lambda limitedData,portfolio,exchangeToTarget,initialValue,start,end,i : [item for sublist in (model(limitedData,Portfolio({asset:(portfolio.getAllAssets()[asset]/n) for asset in list(portfolio.getAllAssets().keys())}),exchangeToTarget,initialValue,start,end,i) for model in TSMOM_list) for item in sublist]


if __name__=="__main__":
    #Get data
    data=pd.read_csv("Bitcoin Historical Data.csv")
    data['DateTime64']=pd.to_datetime(data['Date'])

    start=np.datetime64("2013-01-01")+random.randint(0,365*6)
    end=start+(365*2)

    models = {
        "HODL":HODL,
        "DCA":DCA,
        "TSMOM_30_7":TSMOM_gen(30,7),
        "TSMOM_90_7":TSMOM_gen(90,7),
        "TSMOM_7_7":TSMOM_gen(7,7),
        "TSMOM_7_1":TSMOM_gen(7,1),
        "TSMOM_D":TSMOM_diversify([(7,1),(30,1),(90,1)])
    }

    portfolios={modelName : Portfolio({'USD':1,'BTC':0}) for modelName in list(models.keys())}

    Market=pd.DataFrame(columns=['Day','Total Value'])
    days=int((end-start)/np.timedelta64(1, 'D'))
    amt=1
    for i in range(days):
        Market=Market.append({'Day':start+i,'Total Value':amt},ignore_index=True)
        amt=amt*1.0001854
    Market.index=Market['Day']

    #TODO: NORMALIZE RETURNS
    result=backtest(data,start,end,models,portfolios)

    result['Market']=Market['Total Value']
    ax=result.plot(figsize=(15,10),title="Backtest from %s to %s"%(start,end),ylabel="Return")
    ax.figure.savefig('backtestReturn.png')

    result['Market']=result['Market']-result['HODL Value']
    for modelName in list(models.keys()):
        if modelName!="HODL":
            result[modelName+' Value']=result[modelName+' Value']-result['HODL Value']
    result['HODL Value']=result['HODL Value']-result['HODL Value']
    ax=result.plot(figsize=(15,10),title="Backtest from %s to %s relative to HODL"%(start,end),grid=True,ylabel="Excess Return")
    ax.figure.savefig('backtestExcessReturn.png')

