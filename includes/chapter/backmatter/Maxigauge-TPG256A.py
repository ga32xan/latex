# -*- coding: utf-8 -*-
"""
See https://github.com/ga32xan/Maxigauge-TPG256A for documentation and electronic copy of the code
python Maxigauge-TPG256A.py -h

Created on Thu Nov 16 12:59:26 2017
Author: Mathias Portner, Domenik Zimmermann
Versions: To make it run, install python 3.6
Additional dependencies: matplotlib, numpy
For Windows: Anaconda is a bundled Python version (https://anaconda.org/anaconda/python)
For Linux: See above or 
sudo apt-get install python3 pip, pip install matplotlib, pip install numpy, pip install serial

Edit this file with 4 space indentation

"""

''' This is for the serial connection and throughout the script :)'''
import serial
import time
import os
import datetime as dt

''' This is for all the plotting stuff '''
import matplotlib.pylab as plt
import matplotlib.dates as mdate
import numpy as np

''' This is imported because of the logging facility and command line arguments '''
import argparse # for the argument parsing stuff and -h explanation
import logging	# for logging puposes

''' This is imported because of the module version logging '''
import inspect
import sys
import re

date_fmt = '%d-%m-%Y %H:%M:%S'
datenow = dt.datetime.now().strftime(date_fmt)

''' Create helper when script is used wrong! '''
''' Parses arguments given in command line '''
parser = argparse.ArgumentParser(
            description = 'Reads pressures from Pfeiffer Maxigauge TPG256A and \
			shows interactive graph if wanted',\
            epilog = 'For detailed documentation see source code or visit \
			http://github.com/ga32xan/Maxigauge-TPG256A'\
            )
			
parser.add_argument('--loglevel', '-v',\
                    help = 'Minimum numeric loglevel/serverity: \n \
					Debug, Info, Warning, Error, Critical.\n \
                    This switch does not affect the pressure log, \
					which is always written in the same detail.\
                    Defaults to Warning.',\
                    type = str,\
                    default = 'Warning'\
                   )

parser.add_argument('--programlogfile', '-pl',\
                    help = 'What filename should the pressure log have? \
					Always written to the directory where script is located\
                    Defaults to control.log',\
                    type = str,\
                    default = 'control.log'\
                   )

parser.add_argument('--pressurelogfile', '-l',\
                    help = 'What filename should the pressure log have? Always \
					written to the directory where script is located\
                    Defaults to pressure.log',
                    type = str,\
                    default = 'pressure.log'\
                   )

parser.add_argument('--plot', '-p',\
                    help = 'Plot graph? Do not use outside spyder (Anaconda), yet!\
                    Defaults to False.',
                    action = 'store_true',\
                    #default = False\ #can be omitted since its the default behaviour
                   )

parser.add_argument('--comport', '-c',\
                    help = 'What port to use? Defaults to 8.',
                    type = int,\
                    default = 8\
                   )

arguments = parser.parse_args()

''' Takes argument loglevel and programlogfile from the argparser \
and passes it to the logging facility '''
loglevel = arguments.loglevel   # is str like debug,info, DeBUg or something similar
# compares to available loglevels and transforms into number
numeric_loglevel = getattr(logging, loglevel.upper(), None) 
if not isinstance(numeric_loglevel, int):
    raise ValueError('Invalid log level: %s' % loglevel)

suffix = arguments.programlogfile.split('.')[0]    #filename
ending = arguments.programlogfile.split('.')[1]    #file type
prefix = '%s - '%datenow.replace(':','-')

programlogfile_name = os.getcwd() + '\\' + prefix + suffix + '.' + ending
#print('Program Logging goes to : ' + programlogfile_name)

logging.basicConfig(filename = programlogfile_name,\
                    format = '%(asctime)s %(message)s',\
                    datefmt = '%d-%m-%Y %H:%M:%S',\
                    filemode = 'a',\
                    level = numeric_loglevel\
                   )
				   
''' Takes argument pressurelogfile from the argparser '''
''' Gets and splits command line argument into prefix.ending and returns appended date '''
suffix = arguments.pressurelogfile.split('.')[0]    #filename
ending = arguments.pressurelogfile.split('.')[1]    #file type
prefix = '%s - '%datenow.replace(':','-')
pressurelogfile_name = os.getcwd() + '\\' + prefix + suffix + '.' + ending

''' Takes argument comport from the argparser '''
com_port = arguments.comport

''' Takes argument plot from the argparser '''
''' Boolean to indicate if auto-updating matplotlib-graph is wanted '''
''' Piviledge Error if not executed within Anaconda '''
''' Set to False if script is exucuted from command line '''
''' Set to true if run in IDE (tested: Anaconda) '''
plot = arguments.plot

logging.info('Using COM-Port : ' + str(com_port))
logging.info('Pressure Logging goes to : ' + pressurelogfile_name)
logging.info('Program Logging goes to  : ' + programlogfile_name)
logging.info('Program Debug level is : ' + arguments.loglevel + '(' + str(numeric_loglevel) + ')')
logging.info('Do i plot something? : ' + str(plot))

def read_gauges(ser):
    ''' Reads all 6 channels and returns status and (if applicable) pressure '''
    '''  There is one list for status[CH] called stat and one for pressure[CH] called press returned'''
    logging.debug('##########read_gauges##############')
    ser.flushInput()

    press = []
    stat = []
    for j in range(6): 			# for each channel
        ''' request data for specific channel '''
        send_command(ser, 'PR%i\r\n'%(j+1))  #request channel
        send_command(ser, '\x05')            #enquire data
		
        ''' what the controller returns is something like 'x,x.xxxEsx <CR><LF>' 
        x[Status],[x.xxxEsx] Measurement value (always engineers' format)
        0 Measurement data okay, 1 Underrange, 2 Overrange
        3 Sensor error, 4 Sensor off, 5 No sensor, 6 Identification error
        '''
		
        logging.debug('##########splitting received pressure string##############')
        string=read_port(ser).split(',') 		# splits read string into string[-1],string[0]
        logging.debug(string)
        string_pres=str(string[1])       	#pressure value converted to string
        logging.debug('Read pressure :' + string_pres)
        string_sta=int(string[0][-1])    	#status value converted to int
        logging.debug('Read status :' + str(string_sta))
        press.append(float(string_pres))    	#append float of pressure to press-list
        stat.append(int(string_sta))        	#append int(status) to status list
    return(stat,press)

def send_command(ser,command):
    ''' Takes ascii string 'command' and converts it to bytes to send it over serial connection '''
    logging.debug('##########ser_command##############')
    input = command.encode('utf-8')   #encode as utf-8
    logging.debug('Command string: ' + str(input))
    convinput=to_bytes(input)       #convert to byte sequence
    logging.debug('byte-input (as str repre): ' + str(convinput.decode('utf-8')))
    logging.debug('CTS line: ' + str(ser.cts))
    logging.debug('DSR line: ' + str(ser.dsr))
    ser.write(convinput)            #send to wire
    time.sleep(0.05)
    logging.debug('Send Command: ' + str(input))

def read_port(ser):
    ''' Reads serial port, gets bytes over wire, decodes them with utf-8'''
    ''' and returns string with received message'''
    logging.debug('##########read_port##############')
    logging.debug('Am I outWaiting?: ' + str(ser.out_waiting))
    logging.debug('Am I inWaiting?: ' + str(ser.in_waiting))
    logging.debug('Input buffer size: ' + str(ser.in_waiting))
    logging.debug('CTS line: ' + str(ser.cts))
    logging.debug('DSR line: ' + str(ser.dsr))
    out = ''                            #string to hold the received message, empty one for new reading
    input_buffersize = ser.in_waiting   #input_buffersize: Numbers of bytes received
    if input_buffersize == 0:
        logging.warning('No data in input buffer...No data received')
    while input_buffersize > 0:
        ''' runs through twice to check consistency of received message '''
        ''' if first read msg matches snd read msg the input is believed to be consistend '''
        ''' No errror handling. '''
		''' Program breaks at this point if no meaningfull serial connection is established '''
        logging.debug('Input buffersize: ' + str(input_buffersize))
        logging.debug('...ser.read ...')
        input_buffersize_old = 0
        time.sleep(0.05)
        out += ser.read(64).decode('utf-8')
        logging.debug('accomplished')
        if input_buffersize == input_buffersize_old:
            logging.debug('Received msg: ' + str(out))
            break
        else:
            input_buffersize = input_buffersize_old
    return out
    logging.debug('Received msg: ' + str(out))

def test_connection(ser):
    logging.debug('##########test_connection##############')
    ''' Unimplemented testing routine to test the serial connection object passed as ser '''
    send_command(ser,'PR%i\r\n'%(j+1))  #request Channel 1-6
    send_command(ser,'\x05')            #enquire data
    read_port(ser)
    if True:
        ''' !Some Check routine missing! '''

def log_serial_info(ser):
    ''' Get information about the serial connection, prints only if debug loglevel is chosen '''
    logging.debug('##########log_serial_info##############')
    
    logging.debug('############ Information about connection: ############')
    logging.debug('Name of device: ' + ser.name)
    logging.debug('@ port : ' + ser.port)
    logging.debug('Port is open?: ' + str(ser.is_open))
    logging.debug('state of ...')
    logging.debug('   ... CTS line: ' + str(ser.cts))
    logging.debug('   ... DSR line: ' + str(ser.dsr))
    logging.debug('   ...  RI line: ' + str(ser.ri))
    logging.debug('   ...  CD line: ' + str(ser.cd))

    logging.debug('############ Can set values to: ######################')
    logging.debug('port: ' + ser.port)
    logging.debug('baudrate: ' + str(ser.baudrate))
    logging.debug('bitesyze: ' + str(ser.bytesize))
    logging.debug('parity: ' + str(ser.parity))
    logging.debug('stopbits: ' + str(ser.stopbits))
    logging.debug('read_timeout: ' + str(ser.timeout))
    logging.debug('write_timeout: ' + str(ser.write_timeout))
    logging.debug('inter byte timeout: ' + str(ser.inter_byte_timeout))
    logging.debug('software flow control setting: ' + str(ser.xonxoff))
    logging.debug('hardware flow control setting of ... ')
    logging.debug('\t \t \t \t... CTS line: ' + str(ser.rtscts))
    logging.debug('\t \t \t \t... DSR line: ' + str(ser.dsrdtr))
    logging.debug('RS485 settings: ' +  str(ser.rs485_mode))

def log_module_info():
    ''' This will print all the used modules together with their mapping to the logfile '''
    for name, val in sys._getframe(1).f_locals.items():
        if inspect.ismodule(val):

            fullnm = str(val)

            if not '(built-in)' in fullnm and \
               not __name__     in fullnm:
                m = re.search(r"'(.+)'.*'(.+)'", fullnm)
                module,path = m.groups()
                logging.info("%-12s maps to %s" % (name, path))
                if hasattr(val, '__version__'):
                    logging.info("\t Version:" +  val.__version__)
                else:
                    logging.info("\t No version listed in val.__version__")

def init_serial(com_port):
    ''' Initializes serial connection, defaults to COM5 '''
    logging.debug('##########init_serial##############')
    try:
        ser = serial.Serial(timeout=0.5,\
			    baudrate=9600,\
			    stopbits=serial.STOPBITS_ONE,\
			    bytesize=serial.EIGHTBITS,\
			    parity=serial.PARITY_NONE\
			   )    
        ser.port = 'COM' + str(com_port)
        ser.open()
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        if numeric_loglevel < 30: log_serial_info(ser)
        logging.debug('init_serial on COM' + str(com_port) + 'succesfully')
        return ser
    except IndexError as err:
        logging.critical('Opening of com-port failed')
        print('Failed opening serial port at port' + str(ser.port))
        print('Make sure you are on the right COM port and try reloading the console')

def to_bytes(seq):
    ''' Convert a sequence of int/str to a byte sequence and returns it '''
    logging.debug('##########to_serial##############')
    if isinstance(seq, bytes):
        return seq
    elif isinstance(seq, bytearray):
        return bytes(seq)
    elif isinstance(seq, memoryview):
        return seq.tobytes()
    else:
        b = bytearray()
        for item in seq:
            b.append(item)  # this one handles int and str for our emulation and int for Python 3.x
        return bytes(b)
        logging.debug('Byte-conversion for ' + str(seq) + ' done')

def update_terminal(time,labels,pressures):
    """  Print information to the console """
    os.system('cls' if os.name == 'nt' else 'clear')        #clear console screen
    pressures_show=[]
    pressures_last=[]
    for j in range(6):
        pressures_last.append(pressures[j][-1])
    for n,i in enumerate(pressures_last):
        if i==1e10:
            pressures_show.append('\tNAN   ')
        else:
            pressures_show.append(str(i))
    print(time + ': \t ... running ...')
    print('Program Logging goes to  : ' + programlogfile_name)
    print('Pressure Logging goes to : ' + pressurelogfile_name)
    print('#################################################################################################')
    print('#\t' + labels[0] + '\t|\t'  + \
                 labels[1] + ' \t|\t'  + \
                 labels[2] + ' \t|\t'  + \
                 labels[3] + ' \t|\t'  + \
                 labels[4] + ' \t|\t'  + \
                 labels[5] + ' \t#')
    print('#     %s\t|     %s\t|     %s\t|     %s\t|     %s\t|     %s  #' \
    %(pressures_show[0],pressures_show[1],pressures_show[2], \
	  pressures_show[3],pressures_show[4],pressures_show[5]))
    print('#################################################################################################')

def get_labels(ser):
    ''' Get and return all the channel names from the controller '''
    send_command(ser, 'CID\r\n')  # request channel
    ''' Check for ACK '''
    send_command(ser, '\x05')     # enquire data
    labels_raw = read_port(ser).split(',')
    logging.debug('Receiving channel names:')
    logging.debug(labels_raw[0][3:])  # slices the \x06\r\n in beginning of MSG
    logging.debug(labels_raw[1])
    logging.debug(labels_raw[2])
    logging.debug(labels_raw[3])
    logging.debug(labels_raw[4])
    logging.debug(labels_raw[5][:-2])  # slices  ending \r\n'
    labels = [labels_raw[0][3:],\
              labels_raw[1],\
              labels_raw[2],\
              labels_raw[3],\
              labels_raw[4],\
              labels_raw[5][:-2]]
    logging.info('Returning Labels: ' + str(labels))
    return labels
########################################## Main routine ##########################################
if __name__ == '__main__':
    ''' Messy routine that updates the data, plot it and updates the logfile '''
    ''' Every time the program is started and writes to the same logfile a line of # is added '''
    ''' TODO: cleanup, write subroutine update_plot and write_logfile '''
    print('... starting up ...')
    logging.debug('##########main()##############')
    logging.debug(arguments)
    if numeric_loglevel < 30: log_module_info()
        
    logging.info('... starting up ...')
    date_fmt = '%d-%m-%Y %H:%M:%S'
    datenow = dt.datetime.now().strftime(date_fmt)      # get formatted datetime object
    pressures = [[],[],[],[],[],[]] #six membered list of lists that holds pressure data
    ''' 
    [[CH1p1, CH1p2, ..., CH1pn], [CH2p1, CH2p2, ..., CH2pn], ... , [CH6p1, CH6p2, ..., CH6pn]]
    '''
    ser = init_serial(com_port) #initialize at this port
    
    times = []  #  list when pressures are recorded (approximately)
    labels = get_labels(ser)
         
    ''' read gauges, pass serial connection to them, returns (stat,press) '''
    ''' stat = [(int)] = [0,,0,5,5,5] & press = [float] = [1e-1,1e-10,1e-10,2e-2,2e-2,2e-2] '''
    ''' these are to be processed before written to log file '''
    stat,stpre=read_gauges(ser)    
    
    ''' The following creates the labels for the plot '''
    ''' Sensors with pressure > 1e-1 are appended with a rightarrow to indicate the axis '''
    ''' Sensors with pressures < 1e-1 are plotted wit a left-arrow on the left axis '''
    
    labels_begin=labels
        
    ''' Prepares and writes logfile '''  
    times.append(mdate.datestr2num(datenow))            #and append it to times list
    #write header if logfile was never used ...
    header = 'Time\t\t\t\t\t'\
            + labels[0] + '[mbar]\t\t' + labels[1] + '[mbar]\t\t' + labels[2] + '[mbar]\t\t'\
            + labels[3] + '[mbar]\t\t\t' + labels[4] + '[mbar]\t\t\t' + labels[5] + '[mbar]\n'
    #... if logfile was already used add seperator 
    if os.path.isfile(pressurelogfile_name):  
        header = '##################### Program restarted ###################################\n'
    with open(pressurelogfile_name, "a") as logfile:
        logfile.write(header)
    ''' enumerate(stat) returns 0,stat[0] ... 1,stat[1] ... 2,stat[2] ... '''
    labels=['','','','','','']
    for sensor_num,status in enumerate(stat):
        logging.debug('##########updating pressures inside main()##############')
        logging.info('Sensor: ' + str(sensor_num))
        if status == 0:
            logging.info('Channel OK')
            pressures[sensor_num].append(stpre[sensor_num])
            if plot:
                if pressures[sensor_num][-1] > 1e-1:
                    labels[sensor_num] = labels_begin[sensor_num]+ \
					    r' $\rightarrow$ %.2e mbar'%pressures[sensor_num][-1]
                elif pressures[sensor_num][-1] <= 1e-1:
                    labels[sensor_num] = labels_begin[sensor_num]+ \
					    r' $\leftarrow$ %.2e mbar'%pressures[sensor_num][-1]
        elif status == 1:
            logging.warning('Channel Underrange')
            pressures[sensor_num].append(1e10)
            if plot: labels[sensor_num] = labels_begin[sensor_num]+' - Underrange'
        elif status == 2:
            logging.warning('Channel Overrange')
            pressures[sensor_num].append(1e10)
            if plot:  labels[sensor_num] = labels_begin[sensor_num]+' - Overrange'
        elif status == 3:
            logging.error('Channel Error')
            pressures[sensor_num].append(1e10)
            if plot:  labels[sensor_num] = labels_begin[sensor_num]+' - Error'
        elif status == 4:
            logging.info('Channel Off')
            pressures[sensor_num].append(1e10)
            if plot:  labels[sensor_num] = labels_begin[sensor_num]+' - Off'
        elif status == 5:
            logging.info('Channel Not found')
            pressures[sensor_num].append(1e10)
            if plot:  labels[sensor_num] = labels_begin[sensor_num]+' - Not found'
        elif status == 6:
            logging.error('Channel Identification Error')
            pressures[sensor_num].append(1e10)
            if plot: labels[sensor_num] = labels_begin[sensor_num]+' - Identification error'
    with open(pressurelogfile_name, "a") as logfile:
        logfile.write("%s\t\t%.2e\t\t%.2e\t\t%.2e\t\t%.2e\t\t\t%.2e\t\t\t%.2e\n"\
		%(datenow,\
		  pressures[0][0],pressures[1][0],pressures[2][0],\
		  pressures[3][0],pressures[4][0],pressures[5][0]))  
    ''' Prepare plot '''
    if plot:
        logging.debug('Preparing plot')
        fig = plt.figure(figsize=(10,6),dpi=100)
        ax = fig.add_subplot(111)
        plt.ion()                      #autoupdate plot
        plt.yscale('log')

        sens = {} 
        col = ['b','r','g','K','c','y'] #colors

        #For each sensors, choose a different color and plot them all on one axis
        for j in range(6):
            sens['sen{0}'.format(j)], = \
			    ax.plot(times, pressures[j], '.', ls = '-', color = col[j], label=labels[j])
        #configure left axis
        ax.set_ylim(1e-12,1e-4)
        ax.set_xlabel('Time')
        ax.set_ylabel('Pressure [mbar]')

        ax.legend()
        plt.gca().xaxis.set_major_formatter(mdate.DateFormatter(date_fmt))
        plt.gcf().autofmt_xdate()

        ax2 = ax.twinx()
        #Plot every sensor with a pressure > 1e-1 on the second axis
        for j in range(6):
            if pressures[j][-1] > 1e-1:
                sens['sen{0}'.format(j)], = ax2.plot(times, pressures[j], '.', ls = '-', color = col[j])
        #configure right axis            
        ax2.set_ylim(1e-1,1e3)
        ax2.set_yscale('log')
        ax2.set_ylabel('Pressure [mbar]')
    
    logging.info('Start Looping')
    while True:
        logging.debug('Loop-Top')
        ''' Keep Com port open for only a short amount of time so that '''
		''' if the program is killed it is most likely in a closed state '''
        ''' This should be done via a try: except: statement to make it exit nicely '''
        labels=['','','','','','']
        ''' Continuously read data '''
        if ser.is_open:
            status,pre = read_gauges(ser)
            ser.close()
        else:
            ser.open()
            status,pre = read_gauges(ser)
            ser.close()
        
        ''' Keep track of changing labels - Crashes program when labels are changed! '''
        """
        labels_old = labels
        if not labels_old == labels:
            with open(pressurelogfile_name, "a") as logfile:
                logfile.write('#labelschanged')
                logfile.write('Time\t\t\t\t\t'\
               + labels[0] + '[mbar]\t\t' + labels[1] + '[mbar]\t\t' + labels[2] + '[mbar]\t\t'\
               + labels[3] + '[mbar]\t\t\t' + labels[4] + '[mbar]\t\t\t' + labels[5] + '[mbar]\n')
        """
        datenow = dt.datetime.now().strftime(date_fmt)
        times.append(mdate.datestr2num(datenow))
        
        ''' To update the legend when a sensor is switched on/off '''
		''' we have to check every time we read a value '''
        ''' Updates values in pressure lists '''
        if plot: ax.legend_.remove()
        for num,sensor in enumerate(status):
            if sensor == 0:
                pressures[num].append(pre[num])
                if plot:
                    if pressures[num][-1] > 1e-1:
                        labels[num] = labels_begin[num]+r' $\rightarrow$ %.2e mbar'%pressures[num][-1]
                    elif pressures[num][-1] <= 1e-1:
                        labels[num] = labels_begin[num]+r' $\leftarrow$ %.2e mbar'%pressures[num][-1]
            elif sensor == 1:
                pressures[num].append(1e10)
                labels[num] = labels_begin[num]+' - Underrange'
            elif sensor == 2:
                pressures[num].append(1e10)
                labels[num] = labels_begin[num]+' - Overrange'
            elif sensor == 3:
                pressures[num].append(1e10)
                labels[num] = labels_begin[num]+' - Error'
            elif sensor == 4:
                pressures[num].append(1e10)
                labels[num] = labels_begin[num]+' - Off'
            elif sensor == 5:
                pressures[num].append(1e10)
                labels[num] = labels_begin[num]+' - Not found'
            elif sensor == 6:
                pressures[num].append(1e10)
                labels[num] = labels_begin[num]+' - Identification error'
        
        ''' Write to log '''
        with open(pressurelogfile_name, "a") as logfile:
            logfile.write('%s\t\t%.2e\t\t%.2e\t\t%.2e\t\t%.2e\t\t\t%.2e\t\t\t%.2e\n'\
			%(datenow,\
			  pressures[0][-1],pressures[1][-1],pressures[2][-1],\
			  pressures[3][-1],pressures[4][-1],pressures[5][-1]))
        ''' Update console output '''
        update_terminal(datenow,labels_begin,pressures)
        ''' Update plot '''
        if plot:
            for j in range(6):
                sens['sen{0}'.format(j)].set_xdata(times)
                sens['sen{0}'.format(j)].set_ydata(pressures[j])
                sens['sen{0}'.format(j)].set_label(labels[j])
            #Set new 'best' place for legand
            ax.legend(loc = 'best')
            #dynamically updating axis range, showing all data
            ax.set_xlim(times[0]-(times[1]-times[0]),times[-1]+(times[1]-times[0]))
            #asis range: 12h
            #ax.set_xlim(dt.datetime.now()-dt.timedelta(hours=12),times[-1]+(times[1]-times[0]))
plt.pause(1)