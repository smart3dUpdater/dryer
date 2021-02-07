#!/usr/bin/env python
'''
Software system monitor for Dryer
---------------------------
Autor: Smart 3D
Version: 1.1
'''

__author__ = "Smart 3D"
__email__ = "smart3d.updater@gmail.com"
__version__ = "1.1"

import io
import os
import time
from time import time as actual_time
import updater as u
from configparser import ConfigParser

start_time = 0
end_time = 0




def health_status():
    services_running = u.check_health()
    services_configurated = u.get_config_services()
    u.debug_print(f'services_running: {services_running}')
    u.debug_print(f'services_configurated: {services_configurated}')
    for service in services_running:
        u.debug_print(f'Servicio: {service}') 
        if services_running[service] != 'UP':
            u.debug_print(f'Service: {service} is working with failures')
            return False
    services = services_running.keys()
    for service in services_configurated:
        if service not in services:
            services_configurated = u.get_config_services(file=u.BACKUP_PATH)
            for service in services_configurated:
                if service not in services:
                    u.debug_print(f'Service: {service} IS NOT RUNIING!')
                    return False
    u.debug_print('The services are runnig ok' )
    return True

if __name__ == '__main__':
    u.debug_print('Reset Flags ... ')
    u.set_update_status(u.UPDATE_STATUS[2])
    u.debug_print('Done\nCheck services ... ')
    if health_status() != True:
        u.debug_print('Services Down, restarting')
        u.restart_services()
    u.debug_print('Services restarteds ...')
    check_health = True
    past_status = 0
    u.debug_print('Begin controll ... ')
    while True:
        status = u.check_update_status()
        if status.get('upgrade') == u.UPDATE_STATUS[6]:
            u.debug_print("Updating...")
            u.update_routine()
            u.debug_print('Done')

        if check_health == True:
            start_time = actual_time()
            check_health = False
            actual_status = health_status()
            if actual_status == False:
                u.debug_print("service DOWN")
                if actual_status == past_status:
                    u.restart_services()
                else:
                    past_status = actual_status
            else:
                past_status = actual_status    
        if actual_time()-start_time > 30:
            check_health = True


