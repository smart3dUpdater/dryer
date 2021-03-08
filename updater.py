#!/usr/bin/env python
'''
Software updater for Dryer
---------------------------
Autor: Smart 3D
Version: 1.1
'''

__author__ = "Smart 3D"
__email__ = "smart3d.updater@gmail.com"
__version__ = "1.1"

import io
import os
import ast
import json
import yaml
import time
from time import time as t
import subprocess
from threading import Thread
from configparser import ConfigParser
from socket import create_connection, gethostbyname
from colorama import init, Fore, Back, Style

DEBUG = False
# Hola
# hay que instalar en la raspi: sudo apt install gnupg2 pass

CONFIG_PATH = "/home/pi/config-files/config.ini"
DOCKER_COMPOSE_PATH = '/home/pi/docker-compose.yml'
BACKUP_PATH = '/home/pi/backup.yml'
UPDATE_STATUS = ("in_progress", "success", "await", "error", "cancel", 'downloaded', 'make')


def set_progress_status(value,config="upgrade",key="progress"):
    try:
        config_object = ConfigParser()
        config_object.read(CONFIG_PATH)
        u = config_object[config]
        v = str(value)
        u[key] = v.replace('\n'," ")
        with open(CONFIG_PATH, 'w') as conf:
            config_object.write(conf)
            conf.close()
        return
    except Exception as error:
        print('write error', error)
        return

def debug_print(*args, end='\n'):
    if DEBUG:
        print(*args,end=end)
    else:
        msn = args[0]
        print(msn)
        m = str(msn)
        m.strip("\n")
        set_progress_status(value=m,config="upgrade",key="progress")

def print_error(msn):
    if DEBUG:
        init(autoreset=True)
        debug_print(Fore.RED+Style.BRIGHT+f'{msn}')
    else:
        print(msn)
        m = str(msn)
        m.strip("\n")
        set_progress_status(value=m,config="upgrade",key="progress")

def print_warning(msn):
    if DEBUG:
        init(autoreset=True)
        debug_print(Fore.YELLOW+Style.BRIGHT+f'{msn}')
    else:
        print(msn)
        m = str(msn)
        m.strip("\n")
        set_progress_status(value=m,config="upgrade",key="progress")

def print_acert(msn=' Done'):
    if DEBUG:
        init(autoreset=True)
        debug_print(Fore.GREEN+Style.BRIGHT+f'{msn}')
    else:
        print(msn)
        m = str(msn)
        m.strip("\n")
        set_progress_status(value=m,config="upgrade",key="progress")    



class UpdateDryer:

    def __init__(self):
        self._running = True

    def terminate(self):
        self._running = False

    def restart(self):
        self._running = True

    def check_connection_on_update(self, delay):
        """
        La función comprueba el estado de conectividad una vez cada tiempo\
            de `delay` esté seteado.
            \nSi en algun momento se cae la conectividad, detiene todos los threads\
             (pull) que están corriendo.
        """
        while self._running:
            if check_connection() == False:
                set_update_status("error")
                self._running = False
                break
            time.sleep(delay)

    def download(self):
        """
        Esta función descarga las nuevas versiones del hub de docker.\
        Primero se loguea en la cuenta que esté seteada en el archivo de \
        configuración, luego procede a hacer un pull de la imagen seteada en el \
        archivo de configuración.
        \nSetea en el archivo de configuración, en update:
        \n`success`: Si se pudo hacer el pull de forma exitosa, sin interrupciones.
        \n'`error`: Si no se pudo realizar.
        """
        attempts = 0
        while self._running:
            result = login_acount()
            if result == "Login Succeeded" and self._running:
                result = pull()
                if result == True:
                    # Detenemos el control de conectividad, porque ya se realizó la descarga.
                    self._running = False
                    print_acert('Image downloaded successfully')
                    set_update_status("downloaded")
                    return False
            attempts += 1
            if attempts > 3:
                self._running = False
        set_update_status("error")

def check_connection():
    """
    Función que hace una conexión a google por medio de un socket,\
    retorna `True` si la conexión fue exitosa, o `False` si hubo un error o\
    no se pudo conectar.
    """
    try:
        gethostbyname('www.google.com')
        testConn = create_connection(('www.google.com', 80), 1)
        testConn.close()
        return True
    except Exception as error:
        print_error('Fail')
        debug_print('traceback:')
        print_error(error)
        return False

def check_update_status():
    """
    Esta función comprueba el flag de estado del archivo de configuración en `upgrade`\
    y devuelve un diccionario con su estado.
    """
    try:
        config_object = ConfigParser()
        config_object.read(CONFIG_PATH)
        u = config_object["upgrade"]
        u_keys = [key for key in u]
        u_configs = {}
        for value in u_keys:
            u_configs[str(value)] = u[str(value)]
        return u_configs
    except Exception as error:
        print_error('Fail')
        debug_print('traceback:')
        print_error(error)
        return {'out' : '','error':error}

def get_config(config = "docker"):
    """
    Devuelve un diccionario con todas las configuraciones de \
    Docker (por defecto), las que dejamos por defecto son:
    \n`docker_id` es el ID de la cuenta
    \n`docker_pass` es el pass en la cuenta
    \n`docker_repo` es el repositorio en docker hub
    \nSi encuentra una excepción, devuelve un diccionario con la key\
    `error` y su contenido.
    \nPara traer otra configuración tenemos que indicarlo con el parámetro\
    `config`
    """
    try:
        config_object = ConfigParser()
        config_object.read(CONFIG_PATH)
        d = config_object[config]
        d_keys = [key for key in d]
        d_configs = {}
        for value in d_keys:
            d_configs[str(value)] = d[str(value)]
        debug_print('Get config files ... OK', end='')
        return d_configs
    except Exception as error:
        debug_print('Get config files ...', end='')
        print_error(f'Fail\n{error}')
        return {"error": error}

def bash_command(cmd='', path='.'):
    """
    Esta función realiza procesos de consola, recibe como parametro:
    \n`cmd:` que es un string con el comando a realizar
    \n`path:` que es un string con la ruta relativa (solo si es necesaria)
    \nRetorna un diccionario con dos Keys:
    \n`out:` con la salida de la consola
    \n`error:`con el error si lo tiene, sino, retorna vacío `''`

    """
    pipe = subprocess.Popen(cmd, shell=True, cwd=path,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (out, error) = pipe.communicate()
    pipe.wait()
    return {'out': out.decode("utf-8"), 'error': error.decode("utf-8")}

def login_acount():
    """
    Esta función se desloguea y se vuelve a loguear de la cuenta de docker-hub
    \nEs para que no tenga errores de acceso a la cuenta.
    \nRetorna:
    \n`Login Succeeded:` cuando el proceso es exitoso
    \n`error:` si hubo un problema, ya sea por conectividad u otros.
    """
    try:
        config = get_config()
        if config.get("error") == None:
            user_id = config.get("docker_id")
            passw = config.get("docker_pass")
            bash_command("docker logout")
            response = bash_command(f"docker login -u {user_id} -p {passw}")
            if "Login Succeeded" in response.get("out"):
                debug_print('Login to acount ... OK', end='')
                return "Login Succeeded"
            elif response.get("out") != '':
                raise Exception(response.get("out"))
            return "error"
        else:
            raise Exception(config.get("error"))
    except Exception as error:
        debug_print('Login to acount ...', end='')
        print_error('Fail')
        debug_print('traceback:')
        print_error(error)
        return "error"

def backup_image():
    """
    Función creada para hacer un backup de la imagen que está corriendo\
        antes de hacer un update.
    """
    debug_print('Performing backup from runing images', end='')
    try:
        output = bash_command("docker ps --format='{{json .}}'")
        debug_print('.',end='')
        if output.get('error') == '':
            out = output.get('out').split('\n')
            info = [out[x] for x in range(len(out)) if out[x] != '']
            info = [ast.literal_eval(info[x]) for x in range(len(info))]
            images = [container.get('Image') for container in info]
            to_backup = []
            debug_print('.',end='')
            for image in images:
                if image not in to_backup:
                    to_backup.append(image)
            image = [image.split(':') for image in to_backup]
            backup_to = [f'{i[0]}:backup' for i in image]
            diag = []
            debug_print('.',end='')
            for i in range(len(to_backup)):
                diag.append(bash_command(
                    f'docker tag {to_backup[i]} {backup_to[i]}'))
            debug_print('Performing backup from runing images OK')
            return {'out':'Backup images created','error':''}
        else:
            raise Exception(output.get('error'))
    except Exception as error:
        print_error('Fail')
        debug_print('traceback:')
        print_error(error)
        return {'out':'','error':error}

def get_config_services(file=DOCKER_COMPOSE_PATH):
    """
    Esta función devuelve los nombres de los contenedores que genera el\
        archivo docker-compose.yml\
        \nRetorna una lista con los nombres.
    """
    debug_print('Get services', end='')
    try:
        with open(file, 'r') as file:
            debug_print('.',end='')
            s = yaml.load(file)
            file.close()
            services = s['services']
            debug_print('.',end='')
            service_keys = services.keys()
            serv = [services[a].get('container_name') for a in service_keys]
            debug_print('.',end='')
            debug_print('Get services OK')
            return serv
    except Exception as error:
        print_error('Fail')
        debug_print('traceback:')
        print_error(error)
        return ['error', error]

def run_backup():
    """
    Función que se llama si falla al tratar de correr el compose up,\
        devuelve una lista con el mensaje del bash command:
        \n`KEY out:` mensaje de salida
        \n`KEY error:` mensaje de error, entrega '' cuando no hay errores.        
    """
    debug_print('Runing backup', end='')
    try:
        bash_command('docker-compose down')
        msn = bash_command('docker-compose -f backup.yml up --remove-orphans')
        debug_print('Runing backup OK', )
        return msn
    except Exception as error:
        print_error('Fail')
        debug_print('traceback:')
        print_error(error)
        return {'out': '', 'error': error}

def set_update_status(value,config="upgrade",key="upgrade"):
    try:
        config_object = ConfigParser()
        config_object.read(CONFIG_PATH)
        u = config_object[config]
        v = str(value)
        u[key] = v.replace('\n'," ")
        with open(CONFIG_PATH, 'w') as conf:
            config_object.write(conf)
            conf.close()
        debug_print('Set updating status ... OK')
        return
    except Exception as error:
        debug_print('Set updating status ...', end='')
        print_error('Fail')
        debug_print('traceback:')
        print_error(error)
        return

def pull():
    """
    Función para realizar un pull de la imagen de docker.
    \n`True`: cuando la descarga fue exitosa
    \n`False`: cuando no se ha podido realizar la descarga.
    """
    config = get_config()
    if config.get("error") == None:
        repo = config.get("docker_repo")
    else:
        debug_print('Pulling image ...', end='')
        print_error('Fail')
        debug_print('traceback:')
        print_error('Error in upgrade flag from config file.')
        return False
    try:
        response = bash_command(f"docker pull {repo}")
        if response["error"] != '':
            raise Exception(response["error"])

        elif f"Image is up to date for {repo}" in response["out"]:
            debug_print('Pulling image DONE')
            return True
        elif response['out'] != '' or response['error'] != '':
            if pull():
                debug_print('Pulling image DONE')
                return True
            else:
                raise Exception(
                    "update failed, traceback:\n" + response["out"])
        else:
            raise Exception("update failed, traceback:\n" + response["out"])
    except Exception as error:
        debug_print('Pulling image ', end='')
        print_error('Fail')
        debug_print('traceback:')
        print_error(error)
        return False

def check_health(containers=['all']):
    """
    Funcion que recibe una lista de strings con los nombres de los contenedores
    \nque queremos controlar, básicamente se ve si están UP o no.
    \nDevuelve un diccionario con:
    \n`KEY = Nombre del contenedor a evaluar`
    \n`VALUE = UP o DOWN`
    \nSi aparece una excepción, la función devuelve un diccionario con el valor
    \nde la excepción en forma de:
    \n`KEY = error`
    \n`VALUE = mensaje de error en string`
    \nSi no se especifica la lista de contenedores a verificar, devuelve el estado\
    de todos
    """
    try:
        output = bash_command("docker ps --format='{{json .}}'")
        if output.get('error') == '':
            out = output.get('out').split('\n')
            info = [out[x] for x in range(len(out)) if out[x] != '']
            info = [ast.literal_eval(info[x]) for x in range(len(info))]
            dic = {}
            if containers[0] != 'all':
                for name in containers:
                    for container in info:
                        dic[name] = 'DOWN'
                        if container.get('Names') == name:
                            if "Up" in container.get('Status'):
                                dic[name] = 'UP'
                                break
                            else:
                                dic[name] = 'DOWN'
                                break
            else:
                for container in info:
                    if "Up" in container.get('Status'):
                        dic[container.get('Names')] = 'UP'
                    else:
                        dic[container.get('Names')] = 'DOWN'
            debug_print('Checking health of containers ... DONE', end='')
            return dic
    except Exception as error:
        print_error('Fail')
        debug_print('traceback:')
        print_error(error)
        return {'error': error}

def restart_services(file="default"):
    """
    Esta función reinicia los servicios de Docker a partír de un docker-compose.yml\
        file por defecto. Recibe también como parámetro, el path de un bakup.yml
        \nPrimero revisa que los .yml estén bien y luego hace el restart de todos, si\
        el default falla se ejecuta el backup.
        \nRetorna un diccionario con:
        \n`out`: Mensaje de salida si no hubo un problema (string)
        \n`error`: Mensaje con el detalle del fallo del proceso (string)
        \nSalidas posibles:
        \n{'out': 'Warning, runing on backup mode', 'error': ''}
        \n{'out': 'runing latest', 'error': ''}
        \n{'out': '', 'error': 'error to read the docker-compose file'}
        \n-Otras con valores no especificados. 
    """
    debug_print('Restarting services: ')
    for attempts in range(5):
        try:
            if file == 'default':
                file_integrity = get_config_services()
            else:
                file_integrity = get_config_services(file)
            debug_print('Read files: ...', end='')
            if file_integrity[0] != 'error':
                debug_print('Read files: ... DONE', end='')
                bash_command('docker-compose down')
                health = check_health()
                services = health.keys()
                for status in health:
                    # probar si trae excepción
                    print_warning(f'\nKill container: {status}' )
                    if health[status] == 'UP':
                        msn = [bash_command(
                            f'docker kill {service}') for service in services]
                        msn = [bash_command(
                            f'docker rm {service}') for service in services]
                        bash_command('docker-compose down')
                debug_print('Down services ... DONE', end='')
                if file == 'default':
                    msn = bash_command("docker-compose up -d --remove-orphans")
                    health = check_health(get_config_services())
                else:
                    msn = bash_command(f"docker-compose -f {file} up -d")
                    health = check_health(get_config_services(file))
                for status in health:
                    if health[status] != 'UP':
                        raise Exception(f'Service {status} down')
                debug_print('Up services ... DONE', end='')
                bash_command('docker system prune -f')
                debug_print('Purge system ... DONE', end='')
                if file == BACKUP_PATH:
                    print_warning('Warning, runing on backup mode')
                    return {'out': 'Warning, runing on backup mode', 'error': ''}
                print_acert('Runing latest')
                bash_command('rm -R ~/.config/chromium/Default/ ')
                bash_command('rm -R ~/.cache/chromium')
                return {'out': 'runing latest', 'error': ''}
            else:
                raise Exception(f'error to read the docker-compose file')
        except Exception as error:
            msn = {'out': '', 'error': error}
            if file != 'default':
                print_error('Fail')
                debug_print('traceback:')
                print_error(error)                
                return msn
        return restart_services(file=BACKUP_PATH)

def update_routine(debug=False):
    DEBUG = debug
    # Hacemos backup
    backup_image()
    # Creamos un objeto para hacer el update y lanzamos los threads para el pull
    u = UpdateDryer()
    connection_monitor = Thread(target=u.check_connection_on_update, args=(3, ))
    pull_data = Thread(target=u.download)
    connection_monitor.start()
    pull_data.start()
    connection_monitor.join()
    pull_data.join()
    status = check_update_status()
    if status.get('upgrade') != 'downloaded':
        # Checkeamos cómo salió la descarga.
        # si falló, se cansela la actualización.
        return status.get('upgrade')
    # Reiniciamos los servicios aplicando los cambios (3 intentos)
    status_services = restart_services()
    if status_services.get('error') != '':
        # TODO: run_forced_backup() si falló aquí, es porque falló todo, 
        # hay que correr un backup de archivos no solo de imagen de docker
        # una opción es tener los archivos respaldados en .zip y sobreescribir
        # todo lo que se deba, pero no está implementado por eso retornamos el
        # mensaje del fallo.
        print(f'Falló todo: {status_services}')
        return status_services
    for attempts in range(3):
        services_running = check_health()
        if services_running.get('error'):
            print('error to get runing services')
        else:
            for service in services_running:
                if services_running[service] == 'DOWN':
                    restart_services()
                    break
            set_update_status("success")
            return
    set_update_status("error")
    return 

if __name__ == '__main__':
    time_start = t()
    update_routine()
    time_end = t()
    delta = f'{time_end-time_start}'
    print(f'Update in {delta[0:5]} S')
