# MRW Dipole Test
# Date: 4/10/25
# Release notes

import serial
import time
import pyvisa
import datetime
import yaml
import os
import ctypes

# Load configuration file
def load_config(file_path):
    try:
        with open(file_path,'r',) as f:
            _config=yaml.safe_load(f)
            #print(_config)
            print(f'Load configuration from "{file_path}"')
            return _config
    except FileNotFoundError as e:
        print(f'Error: File "{file_path}" not found. \n{e}')
        log_data(log_file_path, f'Error: File "{file_path}" not found. \n{e}')
        exit()
# User entry
def enter_parameters(parameter):
    # Enter and accept
    _string_Input = input(f"Enter a {parameter}: ")
    # print(f"{parameter}: {_string_Input}")
    # converting to integer
    try:
        return float(_string_Input)
    except ValueError:
        print(f"Invalid input: Please enter a valid {parameter}.")
        exit()

# Configure Keysight N5748A
def open_n5748a(resource_name):
    try:
        _rm=pyvisa.ResourceManager()
        _v5748A_resource=_rm.open_resource(resource_name)
        print("Connected to Keysight 57x8A")
        log_data(log_file_path,'Connected to Keysight 57x8A')
        return _v5748A_resource
    except pyvisa.VisaIOError as e:
        print(f"Error: Could not connect to 5748A {resource_name}.\n{e}")
        log_data(log_file_path, f"Error: Could not connect to 57x8A {resource_name}.{e}")
        exit()

def config_n5748a(coil,resource):
    if coil=='A':
        _model = config_data['Test_Equipment']['Power_Supply_Model_A']
    else:
        _model = config_data['Test_Equipment']['Power_Supply_Model_B']
    _voltage=config_data['Test_Equipment']['Power_Supply_Voltage']
    _current=config_data['Test_Equipment']['Power_Supply_Current_Limit']
    _timeout = config_data['Test_Equipment']['Power_Supply_Timeout']
    resource.timeout = int(_timeout)
    _id=resource.query('*IDN?') #'keysight 57x8A'
    if _model in _id:
        resource.write(_voltage)  # SCPI command to set voltage
        print(f"Voltage set to {_voltage}")
        resource.write(_current)  # SCPI command to set current limit
        print(f"Current limit set to {_current}")
        resource.write(':OUTP OFF')  # SCPI command to disable output
        print("Output disabled")
    else:
        print(f"Incorrect Power Supply Model {_model}!")
        exit()

# Configure Keysight DAQ970A
def open_daq970a(resource_name):
    _model = config_data['Test_Equipment']['DAQ_Model']
    _timeout = config_data['Test_Equipment']['DAQ_Timeout']
    try:
        _rm=pyvisa.ResourceManager()
        _daq970A_resource=_rm.open_resource(resource_name)
        print('Connected to Keysight daq970A')
        log_data(log_file_path, 'Connected to Keysight daq970A')
        _daq970A_resource.timeout = int(_timeout)
        _id = _daq970A_resource.query('*IDN?')
        if _model in _id:
            log_data(log_file_path, f"Correct DAQ Model {_model}!")
            return _daq970A_resource
        else:
            _daq970A_resource.close()
            raise TypeError('Incorrect Model')
    except TypeError as e:
        print(f"Error: Model {e}")
        log_data(log_file_path, f"Incorrect DAQ Model {_model}!")
        exit()
    except pyvisa.VisaIOError as e:
        print(f"Error: Could not connect to DAQ970A {resource_name}.\n{e}")
        log_data(log_file_path, f"Error: Could not connect to DAQ970A {resource_name}.{e}")
        exit()

def config_daq970a(resource, coil):
    _digitize_config_a = config_data['Test_Equipment']['DAQ_Digitize_Config_A']
    _digitize_config_b = config_data['Test_Equipment']['DAQ_Digitize_Config_B']
    if coil=="A":
        resource.write(_digitize_config_a)  # SCPI command to config digitize
        print(f"Digitize set to {_digitize_config_a}")
        log_data(log_file_path, f"Digitize set to {_digitize_config_a}")
    if coil == "B":
        resource.write(_digitize_config_b)  # SCPI command to config digitize
        print(f"Digitize set to {_digitize_config_b}")
        log_data(log_file_path, f"Digitize set to {_digitize_config_b}")

# Configure Magnetometer Serial
def open_serial(config):
    try:
        _ser = serial.Serial(
            port=config['Test_Equipment']['Magnetometer_COM'],
            baudrate=config['Test_Equipment']['Magnetometer_Baud_Rate'],
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            bytesize=serial.EIGHTBITS,
            timeout=2
        )
        print('Connected to Magnetometer FVM-400')
        log_data(log_file_path, 'Connected to Magnetometer FVM-400')
        _ser.write('SC0'.encode())          # X
        time.sleep(float(config['Test_Equipment']['Magnetometer_Write_Delay']))
        _ser.write('SM1'.encode())          # Relative Mode
        time.sleep(float(config['Test_Equipment']['Magnetometer_Write_Delay']))
        _ser.write('SC1'.encode())          # Y
        time.sleep(float(config['Test_Equipment']['Magnetometer_Write_Delay']))
        _ser.write('SM1'.encode())          # Relative Mode
        time.sleep(float(config['Test_Equipment']['Magnetometer_Write_Delay']))
        _ser.write('SC2'.encode())          # Z
        time.sleep(float(config['Test_Equipment']['Magnetometer_Write_Delay']))
        _ser.write('SM1'.encode())          # Relative Mode
        time.sleep(float(config['Test_Equipment']['Magnetometer_Write_Delay']))
        print('Configured to Rel mode')
        log_data(log_file_path, 'Configured to Rel mode')
        return _ser
    except serial.SerialException as e:
        print(f"Error opening with serial port:\n{e}")
        exit()

def magnet_field_test():
    m_array_x=[]
    m_array_y=[]
    m_array_z=[]
    _average_count = int (config_data['Test_Constant']['MAGNET_AVERAGE_COUNT'])
    _time = float(config_data['Test_Equipment']['Magnetometer_Write_Delay'])

    for i in range(_average_count):
        time.sleep(_time)
        print(f"Test# {i}")
        ser_magnetometer.write('?'.encode())
        if ser_magnetometer.in_waiting > 0:
            #_read_data='A\x04A\x04 0.000004,-108638,-107863\rD\x04A\x04A\x04 -8989,-108638,-107863\rD\x04'
            _read_data=str(ser_magnetometer.readline())
            print(f"Received Out: {_read_data}")
            # Parse magnetic field X, Y, Z values
            _start_str="A\\x04"
            _end_str="\\rD"
            _start_index=_read_data.find(_start_str)
            print (f"Start: {_start_index}")
            _end_index=_read_data.find(_end_str,_start_index+1)
            print(f"Start: {_end_index}")
            _m=(_read_data[_start_index+len(_start_str)+1:_end_index])
            log_data(log_file_path, "Magnetometer Reading: " + _m)
            m_s=_m.split(',')
            if len(m_s)==3 and len(m_s[0]) < 10:
                m_array_x.append(float(m_s[0]))
                m_array_y.append(float(m_s[1]))
                m_array_z.append(float(m_s[2]))
    print(m_array_x)
    print(m_array_y)
    print(m_array_z)
    x_average = sum(m_array_x) / len(m_array_x)
    return x_average * pow(10, -9)

def calculate_dipole_moment(coil,volt,curr,magnet,res0,t0):
    _alph = config_data['Test_Constant']['ALPHA']
    _x_dis = config_data['Test_Constant']['X_DISTANCE_MAGNETOMETER']
    _t_target = config_data['Test_Constant']['T_TARGET']
    # Calculate average temperature T
    _r = volt/curr
    t = (_r / res0 - 1) / float(_alph) + t0
    # Calculate Dipole Moment- magnet/2 * L^3 * 10^7 [Am2]
    m = (magnet/2) * pow(float(_x_dis),3) * pow(10, 7)
    # Calculate Target Dipole Moment
    if coil == 'A' or coil=='B':
        m_target = m / (1 + float(_alph) * (float(_t_target) - t))
    else:
        m_target = m
    print(f"R: {_r}; R0: {res0}; T: {t}; T0: {t0}; Alpha: {_alph}; Moment: {m}; Moment Target: {m_target}")
    log_data(log_file_path, f"R: {_r}; R0: {res0}; T: {t}; T0: {t0}; Alpha: {_alph}")
    log_data(log_file_path, f"Moment: {m}; Moment Target: {m_target}")
    return m_target

def coil_volt_test(coil):
    _volt = 0
    try:
        if coil == 'A':
            _volt = v5748A_A_resource.query(':MEAS:VOLT?')
            log_data(log_file_path, f"Coil_A voltage: {_volt}")
        if coil == 'B':
            _volt = v5748A_B_resource.query(':MEAS:VOLT?')
            log_data(log_file_path, f"Coil_B voltage: {_volt}")
        return float(_volt)
    except pyvisa.VisaIOError as e:
        print(f"Error: Could not communicate to 5748A. {e}")
        exit()

def coil_curr_test(coil):
    _average_count = int (config_data['Test_Constant']['CURRENT_AVERAGE_COUNT'])
    _dig_conf_a = config_data['Test_Equipment']['DAQ_Digitize_Config_A']
    _dig_conf_split = str(_dig_conf_a).split(',')
    _timer = float(_dig_conf_split[2])
    if coil == 'A':
        waveform_path = waveform_file_path_A
    else:
        waveform_path = waveform_file_path_B
    try:
        _curr = daq970A_resource.query('READ?')
        _curr_split_str = str(_curr).split(',')
        _count = 0
        for curr in _curr_split_str:
            _current_timer = _count * _timer
            _curr_round = round(_current_timer, 3)
            _curr_timer_log = f'{_curr_round},{curr}'
            save_waveform(waveform_path,  _curr_timer_log)
            _count += 1
        # get last n current reading
        _curr_split_str_n = _curr_split_str[len(_curr_split_str)-_average_count:len(_curr_split_str)-1]
        _curr_split_float_n = [float(x) for x in _curr_split_str_n]
        curr_average = sum(_curr_split_float_n)/len(_curr_split_str_n)
        return curr_average
    except pyvisa.VisaIOError as e:
        print(f"Error: Could not communicate to DAQ970A. {e}")
        exit()

def dipole_test(coil):
    _dipole_moment = 0
    if coil=='A':
        if not config_data['Debug']:
            v5748A_A_resource.write(':OUTP ON')
        log_data(log_file_path, "Output A enabled")
        if config_data['Debug']:
            _curr_meas = 0.066
            _volt_meas = 66
            _magnet_field = 0.0000048
        else:
            _curr_meas = coil_curr_test('A')
            _volt_meas = coil_volt_test('A')
            _magnet_field = magnet_field_test()
        if not config_data['Debug']:
            v5748A_A_resource.write(':OUTP OFF')
        log_data(log_file_path, "Output A disabled")
        _dipole_moment=calculate_dipole_moment('A',_volt_meas,_curr_meas,float(_magnet_field),r0_a,t0_a)
    if coil=='B':
        if not config_data['Debug']:
            v5748A_B_resource.write(':OUTP ON')
        log_data(log_file_path, "Output B enabled")
        if config_data['Debug']:
            _curr_meas = 0.0530973451327434
            _volt_meas = 66
            _magnet_field = 0.0000040
        else:
            _curr_meas = coil_curr_test('B')
            _volt_meas = coil_volt_test('B')
            _magnet_field = magnet_field_test()
        if not config_data['Debug']:
            v5748A_B_resource.write(':OUTP OFF')
        log_data(log_file_path, "Output B disabled")
        _dipole_moment=calculate_dipole_moment('B',_volt_meas,_curr_meas,float(_magnet_field),r0_b,t0_b)
    if coil=='AB':
        if not config_data['Debug']:
            v5748A_A_resource.write(':OUTP ON')
        log_data(log_file_path, "Output A enabled")
        if not config_data['Debug']:
            v5748A_B_resource.write(':OUTP ON')
        log_data(log_file_path, "Output B enabled")
        if config_data['Debug']:
            _magnet_field = 0.000006
        else:
            _magnet_field = magnet_field_test()
        if not config_data['Debug']:
            v5748A_A_resource.write(':OUTP OFF')
        log_data(log_file_path, "Output A disabled")
        if not config_data['Debug']:
            v5748A_B_resource.write(':OUTP OFF')
        log_data(log_file_path, "Output B disabled")
        _dipole_moment = calculate_dipole_moment('AB',99, 99, float(_magnet_field), r0_a, t0_a)
    return round(_dipole_moment, int(config_data['Test_Constant']['Data_Decimal_Num']))

def log_data(path, data):
    with open(path, "a") as file:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
        file.write(f"{timestamp}\t{data} \n")

def save_waveform(waveform_file_path, data):
    with open(waveform_file_path, "a") as file:
        file.write(f"{data}\n")

# Create Test Report
def save_txt_report(config, results):
    _fail_count=0
    # build report header
    name = config['Name']
    version = config['Version']
    copy_right = config['Copyright']
    test_date_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    report_header = f"Test: {name}\nVersion: {version}\nCopyright:{copy_right}\n\nTest Date/Time: {test_date_time}\n\nSN: {sn}\n\n"
    _csv_header = f"{name},{sn},{version},{test_date_time},"

    # build report body
    test_limit_lo = config['Test_Limits']['Dipole_Moment_A_Min']
    if float(results[0]) >= float(test_limit_lo):
        _pass_fail="Pass"
    else:
        _pass_fail="Fail"
        _fail_count+=1
    report_test_a = f'Coil A Dipole Moment Target: {results[0]}\tLower Limit: {test_limit_lo}\tUnit: Am2\t{_pass_fail}\n'
    csv_report_test_a = f'{results[0]},{test_limit_lo},{_pass_fail},'
    test_limit_lo = config['Test_Limits']['Dipole_Moment_B_Min']
    if float(results[1]) >= float(test_limit_lo):
        _pass_fail = "Pass"
    else:
        _pass_fail = "Fail"
        _fail_count += 1
    report_test_b = f'Coil B Dipole Moment Target: {results[1]}\tLower Limit: {test_limit_lo}\tUnit: Am2\t{_pass_fail}\n'
    csv_report_test_b = f'{results[1]},{test_limit_lo},{_pass_fail},'
    test_limit_lo = config['Test_Limits']['Dipole_Moment_AB_Min']
    if float(results[2]) >= float(test_limit_lo):
        _pass_fail = "Pass"
    else:
        _pass_fail = "Fail"
        _fail_count += 1
    report_test_ab = f'Coil A&B Dipole Moment: {results[2]}\tLower Limit: {test_limit_lo}\tUnit: Am2\t{_pass_fail}\n'
    csv_report_test_ab = f'{results[2]},{test_limit_lo},{_pass_fail},'

    report_body = report_test_a + report_test_b + report_test_ab
    _csv_body = csv_report_test_a + csv_report_test_b + csv_report_test_ab
    # build report footer
    if _fail_count <=0:
        report_footer = '\nOverall Result: PASS\n'
        _csv_footer = 'PASS\n'
        report_footer_dis = '\033[32m' + '\nOverall Result: Pass\n'
    else:
        report_footer = '\nOverall Result: FAIL\n'
        _csv_footer = 'FAIL\n'
        report_footer_dis = '\033[31m' + '\nOverall Result: Fail\n'
        #\033[31mThis is red text\033[0m
    report = report_header + report_body + report_footer
    csv_report = _csv_header + _csv_body + _csv_footer
    report_dis = report_header + report_body + report_footer_dis
    print (report_dis)
    # Save test report
    txt_file_path = os.path.join(log_path, f"{sn}_test_report_{datetime.datetime.now().strftime("%Y%m%d%H%M%S")}.txt")
    with open(txt_file_path, "a") as file:
        file.write(report)
        print('\033[37m' + f'TXT file "{txt_file_path}" saved successfully.')

    _csv_file_path = "test_data.csv"
    with open(_csv_file_path, "a") as file:
        file.write(csv_report)
        print(f'CSV file "{_csv_file_path}" saved successfully.')

#===========================================================================================#
# Main Loop
#===========================================================================================#
Config_File_Path='Configuration.yaml'

kernel32 = ctypes.windll.kernel32
handle = kernel32.GetStdHandle(-11)
mode = ctypes.c_uint32()
kernel32.GetConsoleMode(handle, ctypes.byref(mode))
kernel32.SetConsoleMode(handle, mode.value | 0x0004)

# Load Configuration File
config_data = load_config(Config_File_Path)
# Enter DUT MI number
sn = 'MI-' + str(int(enter_parameters('MI')))
if config_data['User_Entry']:
    # Enter and accept T0 and R0 from assembly procedures
    t0_a = enter_parameters('T0_A')
    r0_a = enter_parameters('R0_A')
    t0_b = enter_parameters('T0_B')
    r0_b = enter_parameters('R0_B')
else:
    t0_a = float(config_data['Test_Constant']['T0_A'])
    r0_a = float(config_data['Test_Constant']['R0_A'])
    t0_b = float(config_data['Test_Constant']['T0_B'])
    r0_b = float(config_data['Test_Constant']['R0_B'])
print(f"{sn}; T0_A:{t0_a}; R0_A:{r0_a}; T0_B:{t0_b}; R0_B:{r0_b}")

for loop in range(int(config_data['Loop_Number'])):
    test_data = []
    try:
        # Create log file
        log_path = os.path.join(os.getcwd(),sn)
        if not os.path.exists(log_path):
            os.makedirs(log_path)
        _date = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file_path = os.path.join(log_path, f"{sn}_data_log_{_date}.txt")
        # Log file title
        log_data(log_file_path,config_data['Log_Title'])
        log_data(log_file_path, sn)
        log_data(log_file_path, f'Loop#: {loop+1}')
        log_data(log_file_path, f"T0_A={t0_a}; R0_A={r0_a}; T0_B={t0_b}; R0_B={r0_b}")
        log_data(log_file_path, 'load Configuration')
        for con in str(config_data).split(','):
            log_data(log_file_path,con)
        # Build waveform file path
        waveform_file_path_A = os.path.join(log_path, f"{sn}_coil_A_current_waveform{_date}.csv")
        waveform_file_path_B = os.path.join(log_path, f"{sn}_coil_B_current_waveform{_date}.csv")

        if not config_data['Debug']:
            # Config Power Supply
            v5748A_A_resource=open_n5748a(config_data['Test_Equipment']['Power_Supply_A_Resource_Name'])
            config_n5748a('A',v5748A_A_resource)
            v5748A_B_resource=open_n5748a(config_data['Test_Equipment']['Power_Supply_B_Resource_Name'])
            config_n5748a('B',v5748A_B_resource)

            # Config DAQ Configuration
            daq970A_resource = open_daq970a(config_data['Test_Equipment']['DAQ_Resource_Name'])

            # Configure the Magnetometer Serial Port
            ser_magnetometer=open_serial(config_data)

        # Test #1 - Coil A Dipole Test
        print("Dipole Test #1")
        log_data(log_file_path,'Test #1')
        if not config_data['Debug']:
            config_daq970a(daq970A_resource, 'A')
        test_data.append(dipole_test('A'))

        # Test #2 - Coil B Dipole Test
        print('Dipole Test #2')
        log_data(log_file_path,'Test #2')
        if not config_data['Debug']:
            config_daq970a(daq970A_resource, 'B')
        test_data.append(dipole_test('B'))

        # Test #3 - Coil A & B Dipole Test
        print('Dipole Test #3')
        log_data(log_file_path,'Test #3')
        test_data.append(dipole_test('AB'))

        print(test_data)
        # Create Test Report
        save_txt_report(config_data, test_data)

        # Clear Resources
        if not config_data['Debug']:
            v5748A_A_resource.close()
        print('Close 5748A_A resource.')
        if not config_data['Debug']:
            v5748A_B_resource.close()
        print('Close 5748A_B resource.')
        if not config_data['Debug']:
            ser_magnetometer.close()
        print('Close FVM-400 resource.')
        if not config_data['Debug']:
            daq970A_resource.close()
        print('Close DAQ970A resource.')
        if int(config_data['Loop_Number']) > 1:
            time.sleep(int(config_data['Loop_Delay']))
        print(f'Loop Number: {loop+1}')

    finally:
        print('End of Dipole Test.')
#===========================================================================================#
# End Loop
#===========================================================================================#
