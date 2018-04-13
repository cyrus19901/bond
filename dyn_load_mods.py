import json
import sched
import subprocess
import time

import datetime
from resin import Resin

import core.config_parser as config
import core.data_access as dao
import core.helper as helper
from core.abstract.bond import InputConfiguration, Configuration

PRODUCTION_CHAIN = 'production.pkl'
CONSUMPTION_CHAIN = 'consumption.pkl'
JSON = 'paul#0@slock.it.json'
RESIN_DEVICE_UUID = '734e348be116e254fcc7a6f46708e96a'
TOKEN = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6MzQwNTAsInVzZXJuYW1lIjoiZ2hfY2VyZWFsa2lsbCIsImVtYWlsIjoiZGVwcmF6ekBnbWFpbC5jb20iLCJjcmVhdGVkX2F0IjoiMjAxOC0wMi0xNVQxMDozMjozOC4wMTlaIiwiZmlyc3RfbmFtZSI6IlBhdWwiLCJsYXN0X25hbWUiOiJEZXByYXoiLCJjb21wYW55IjoiIiwiYWNjb3VudF90eXBlIjoicGVyc29uYWwiLCJqd3Rfc2VjcmV0IjoiNkpZWVBUUEpSTDVaQTZRM0ZUUkE2VU1OQ0w3QVFEVlIiLCJoYXNfZGlzYWJsZWRfbmV3c2xldHRlciI6ZmFsc2UsInNvY2lhbF9zZXJ2aWNlX2FjY291bnQiOlt7ImNyZWF0ZWRfYXQiOiIyMDE4LTAyLTE1VDEwOjMyOjM4LjAxOVoiLCJpZCI6MTE1MzcsImJlbG9uZ3NfdG9fX3VzZXIiOnsiX19kZWZlcnJlZCI6eyJ1cmkiOiIvcmVzaW4vdXNlcigzNDA1MCkifSwiX19pZCI6MzQwNTB9LCJwcm92aWRlciI6ImdpdGh1YiIsInJlbW90ZV9pZCI6IjI5MjM0MTMiLCJkaXNwbGF5X25hbWUiOiJjZXJlYWxraWxsIiwiX19tZXRhZGF0YSI6eyJ1cmkiOiIvcmVzaW4vc29jaWFsX3NlcnZpY2VfYWNjb3VudCgxMTUzNykiLCJ0eXBlIjoiIn19XSwiaGFzUGFzc3dvcmRTZXQiOmZhbHNlLCJuZWVkc1Bhc3N3b3JkUmVzZXQiOmZhbHNlLCJwdWJsaWNfa2V5Ijp0cnVlLCJmZWF0dXJlcyI6W10sImludGVyY29tVXNlck5hbWUiOiJnaF9jZXJlYWxraWxsIiwiaW50ZXJjb21Vc2VySGFzaCI6IjkwYWZiZTRkZThkNmU5MDBmYWJiMTIyMzU1MjE4ZWMyNTkyOWRhYTY1NDMyYzcwZjQ0OGRkZWNlZDQxNmVkN2IiLCJwZXJtaXNzaW9ucyI6W10sImF1dGhUaW1lIjoxNTIyOTMwMTM5NTgyLCJhY3RvciI6MjU2MTAwMSwiaWF0IjoxNTIzNjA4ODg2LCJleHAiOjE1MjQyMTM2ODZ9.dNZFqkvt8OY9oPyyW14nubn5j6jHBTEafsT4ku0JuL8'


def read_config():
    """
    Device variable must be added in the services variable field on resin.io dashboard.
    Yeah, I know.
    :param device_id: Device UUID from resin.io dashboard.
    :return: Dict from json parsed string.
    """
    resin = Resin()
    resin.auth.login_with_token(TOKEN)
    app_vars = resin.models.environment_variables.device.get_all(RESIN_DEVICE_UUID)
    config_json_string = next(var for var in app_vars if var['env_var_name'] == 'config')
    return json.loads(config_json_string['value'])


def print_config():
    if configuration.production is not None:
        for item in configuration.production:
            print('Energy Production Module: ' + item.energy.__class__.__name__)
            print('Carbon Emission Saved: ' + item.carbon_emission.__class__.__name__)
    if configuration.consumption is not None:
        [print('Energy Consumption Module: ' + item.energy.__class__.__name__) for item in configuration.consumption]
    print('EWF Client: ' + configuration.client.__class__.__name__)


def start_ewf_client():
    subprocess.Popen(["/usr/local/bin/ewf-client", "--jsonrpc-apis", "all", "--reserved-peers",
                      "/Users/r2d2/software/ewf/tobalaba-reserved-peers"], stdout=subprocess.PIPE,
                     stderr=subprocess.PIPE)
    print('waiting for ewf-client...\n\n')
    time.sleep(60)


def print_production_results(config: Configuration, item: InputConfiguration):
    print("==================== PRODUCTION INPUT READ ===========================")
    try:
        production_local_chain = dao.DiskStorage(PRODUCTION_CHAIN)
        last_local_chain_hash = production_local_chain.get_last_hash()
    except Exception as e:
        print('ERROR: Writing or reading files')
        return
    try:
        last_remote_chain_hash = config.client.last_hash(item.origin)
        print('Local and Remote chain sync:')
        print(last_local_chain_hash == last_remote_chain_hash)
        print('----------')
    except Exception as e:
        print('ERROR: Reading hash from blockchain')
        return
    try:
        produced_data = dao.read_production_data(item, last_local_chain_hash)
    except Exception as e:
        print('ERROR: Reading from remote api.')
        return
    try:
        file_name_created = production_local_chain.add_to_chain(produced_data)
    except Exception as e:
        print('ERROR: Writing to local chain of files.')
        return
    try:
        print('Produced Energy:')
        if produced_data.raw_energy:
            print(produced_data.raw_energy.measurement_epoch)
            print(produced_data.raw_energy.accumulated_power)
        print('----------')
        print('Carbon Emission Today:')
        if produced_data.raw_carbon_emitted:
            print(produced_data.raw_carbon_emitted.measurement_epoch)
            print(produced_data.raw_carbon_emitted.accumulated_co2)
        print('----------')
        print('Sent to Blockchain:')
        print(produced_data.produced.to_dict())
        print('----------')

    except Exception as e:
        print('ERROR: Converting results to print.')
        return
    try:
        print('Lash Remote Hash:')
        print(config.client.last_hash(item.origin))
        print('----------')
        tx_receipt = config.client.mint(produced_data.produced, item.origin)
        print('Receipt Block Number: ' + str(tx_receipt['blockNumber']))
        print('-------------------')
        print('New Remote Hash:')
        print(config.client.last_hash(item.origin))
        print('----------')
    except Exception as e:
        print('ERROR: Reading or writing to the blockchain.')
        return
    try:
        print('New Local Hash:')
        print(production_local_chain.get_last_hash())
        print('----------')
        print('New Local File:')
        print(file_name_created)
        print('----------\n')
    except Exception as e:
        print('ERROR: Reading from local chain of files.')
        return


def print_consumption_results(config: Configuration, item: InputConfiguration):
    print("==================== CONSUMPTION INPUT READ ===========================")
    try:
        consumption_local_chain = dao.DiskStorage(CONSUMPTION_CHAIN)
        last_local_chain_hash = consumption_local_chain.get_last_hash()
    except Exception as e:
        print('ERROR: Writing or reading files')
        return
    try:
        last_remote_chain_hash = config.client.last_hash(item.origin)
        print('Local and Remote chain sync:')
        print(last_local_chain_hash == last_remote_chain_hash)
        print('----------')
    except Exception as e:
        print('ERROR: Reading hash from blockchain')
        return
    # Get the remote data.
    try:
        consumed_data = dao.read_consumption_data(item, last_local_chain_hash)
    except Exception as e:
        print('ERROR: Reading from remote api.')
        return
    try:
        file_name_created = consumption_local_chain.add_to_chain(consumed_data)
    except Exception as e:
        print('ERROR: Writing to local chain of files.')
        return
    try:
        print('Produced Energy:')
        print(helper.convert_time(consumed_data.raw_energy.measurement_epoch))
        print(consumed_data.raw_energy.accumulated_power)
        print('----------')
        print('Sent to Blockchain:')
        print(consumed_data.consumed.to_dict())
        print('----------')

    except Exception as e:
        print('ERROR: Converting results to print.')
        return
    try:
        print('Lash Remote Hash:')
        print(config.client.last_hash(item.origin))
        print('----------')
        tx_receipt = config.client.mint(consumed_data.consumed, item.origin)
        print('Receipt Block Number: ' + str(tx_receipt['blockNumber']))
        print('-------------------')
        print('New Remote Hash:')
        print(config.client.last_hash(item.origin))
        print('----------')
    except Exception as e:
        print('ERROR: Reading or writing to the blockchain.')
        return
    try:
        print('New Local Hash:')
        print(consumption_local_chain.get_last_hash())
        print('----------')
        print('New Local File:')
        print(file_name_created)
        print('----------\n')
    except Exception as e:
        print('ERROR: Reading from local chain of files.')
        return


def log():
    print('\n\n¸.•*´¨`*•.¸¸.•*´¨`*•.¸ Results ¸.•*´¨`*•.¸¸.•*´¨`*•.¸\n')
    if configuration.production:
        [print_production_results(configuration, item) for item in configuration.production]
    if configuration.consumption:
        [print_consumption_results(configuration, item) for item in configuration.consumption]


if __name__ == '__main__':

    scheduler = sched.scheduler(time.time, time.sleep)

    infinite = True
    future = datetime.datetime.now()
    time_sched = '11:35'
    hour, min = tuple(time_sched.split(':'))
    future.replace(hour=hour, min=min)
    while infinite:
        print('===================== READING CONFIG ==================')
        configuration = config.parse(json.load(open(JSON)))
        # configuration = config.parse(read_config())
        print('`•.,,.•´¯¯`•.,,.•´¯¯`•.,, Config ,,.•´¯¯`•.,,.•´¯¯`•.,,.•´\n')
        print_config()

        print('===================== WAITING ==================')
        scheduler.enterabs(time=time.time() + 3, priority=1, action=log, argument=())
        scheduler.run()
