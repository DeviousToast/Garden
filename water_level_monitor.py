#!/usr/bin/python
import argparse
from email.mime.text import MIMEText
import signal
import smtplib
import sys
import time

# From apt-get install python-dev python-setuptools && easy_install rpi.gpio
import RPi.GPIO as GPIO

# From https://github.com/adafruit/Adafruit-Raspberry-Pi-Python-Code
import Adafruit_ADS1x15.Adafruit_ADS1x15 as Adafruit_ADS1x15


# Non-flag globals.  Do not modify.
ADS1015 = 0x00  # 12-bit ADC
ADS1115 = 0x01  # 16-bit ADC


def ReadWaterLevel():
  """Reads the current water level and returns a percentage full."""
  adc = Adafruit_ADS1x15.ADS1x15(ic=ADS1015)
  volts = adc.readADCSingleEnded(channel=0, pga=4096, sps=250)
  print 'Volts read from sensor: %s' % volts
  return volts


def SendEmail(args, water_level):
  """Sends a water level too low email to the recipient."""
  if not args.enable_email:
    print 'Email disabled.  Not sending.'
    return

  message = MIMEText(args.email_body_template % water_level)
  message['Subject'] = args.email_subject
  message['From'] = args.email_from_address
  message['To'] = args.email_to_address

  smtp = smtplib.SMTP_SSL(local_hostname=args.mail_server_local_hostname)
  smtp.connect(host=args.mail_server_ip, port=args.mail_server_port)
  #smtp.set_debuglevel(1)
  smtp.ehlo()
  smtp.sendmail(
      args.from_address,
      args.to_address.split(','),
      message.as_string())
  smtp.quit()


def HandleSignal(signal, frame):
  print 'Exiting...'
  sys.exit(0)


def CheckArgs(args):
  if args.enable_email:
    if not (
        args.email_to_address and
        args.email_from_address and
        args.email_subject and
        args.email_body_template and
        args.email_server_ip and
        args.email_server_port and
        args.email_server_local_hostname):
      raise ValueError(
          'The following flags are required when --enable_email is True:\n'
          '--email_to_address, --email_from_address, --email_subject, '
          '--email_body_template, --email_server_ip, --email_server_port, '
          '--email_server_local_hostname')
    if not r'%s' in args.email_body_template:
      raise ValueError(
          'Email body template must have a %%s placeholder for the '
          'water level.')

  if args.sample_period_sec < 1:
    raise ValueError('--sample_period too short.  Must be > 1 second.')

  if (args.minimum_water_level < 0 or
      args.minimum_water_level >= 2600):
    raise ValueError('--minimum_water_level must be between 0 and 2599.')


def ParseArgs():
  arg_parser = argparse.ArgumentParser()

  arg_parser.add_argument(
      '--enable_email', action='store_true',
      help='Set to enable sending email alerts.')
  arg_parser.add_argument(
      '--email_to_address', type=str, default='',
      help='Email address to which to send low water alerts.')
  arg_parser.add_argument(
      '--email_from_address', type=str, default='',
      help='Email address from which to send low water alerts.')
  arg_parser.add_argument(
      '--email_subject', type=str,
      default='Garden water level too low',
      help='Email subject for low water alerts.')
  arg_parser.add_argument(
      '--email_body_template', type=str,
      default='Garden water level is too low.  Current water level is %s.',
      help=('Email body template for low water alerts.  Must contain exactly '
            'one \'%%s\' placeholder for the water level value.'))
  arg_parser.add_argument(
      '--email_server_ip', type=str, default='127.0.0.1',
      help='Email server IP address.')
  arg_parser.add_argument(
      '--email_server_port', type=int, default=465,
      help='Email server port.')
  arg_parser.add_argument(
      '--email_server_local_hostname', type=str, default='garden',
      help='Email server hostname to use during the EHLO.')

  arg_parser.add_argument(
      '--sample_period_sec', default=3600, type=int,
      help='Time in seconds to wait between checking water level.')
  arg_parser.add_argument(
      '--minimum_water_level', default=1200, type=int,
      help='The minimum water level before sending an alert.')

  args = arg_parser.parse_args()
  try:
    CheckArgs(args)
  except ValueError as e:
    print e.message
    sys.exit(1)
  return args


def Main(args):
  while True:
    water_level = ReadWaterLevel()
    if water_level <= args.minimum_water_level:
      # TODO: Store results in a file for later analysis.
      print 'Water level is too low (%s).' % water_level
      SendEmail(args, water_level)
    else:
      print 'Current water level is %s.' % water_level
    time.sleep(args.sample_period_sec)


if __name__ == '__main__':
  signal.signal(signal.SIGINT, HandleSignal)
  Main(ParseArgs())
  print 'Shut down'

