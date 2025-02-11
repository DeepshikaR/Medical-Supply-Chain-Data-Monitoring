import random


vehicleIDs = [i for i in range(1,11)]    ## 10 vehicles
warehouseIDs = [i for i in range(1,6)]   ## 5 warehouses
hospitalIDs = [i for i in range(1,11)]   ## 10 hospitals
factoryIDs = [1,2,3]                     ## 3 factories
orderID = 0
vaccineIDs = [i for i in range(1,6)]     # 1 to 5 (5 different vaccines)


### ASSUMPTIONS ####
### Warehouse i has vaccine i 

warehouse_stock = {}

for i in warehouseIDs:
    warehouse_stock[i]= 0


### MAPPING - WAREHOUSE TO HOSPITAL TIMES (HOURS)

time_map = []
for i in warehouseIDs:
    temp = random.sample(range(1,11),10)
    time_map.append(temp)



