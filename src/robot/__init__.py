#  Copyright 2008 Nokia Siemens Networks Oyj
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.


import sys

if __name__ == '__main__':
    sys.stderr.write("Use 'runner' or 'rebot' for executing.\n")
    sys.exit(252)  # 252 == DATA_ERROR

if 'pythonpathsetter' not in sys.modules:
    import pythonpathsetter
from output import Output, CommandLineMonitor, SYSLOG
from conf import RobotSettings, RebotSettings
from running import TestSuite
from serializing import RobotTestOutput, RebotTestOutput, SplitIndexTestOutput
from errors import DataError, Information, INFO_PRINTED, DATA_ERROR, \
        STOPPED_BY_USER, FRAMEWORK_ERROR
from variables import init_global_variables
import utils

__version__ = utils.version


def run_from_cli(args, usage):
    _run_or_rebot_from_cli(run, args, usage, pythonpath='pythonpath')

def rebot_from_cli(args, usage):
    _run_or_rebot_from_cli(rebot, args, usage)

def _run_or_rebot_from_cli(method, cliargs, usage, **argparser_config):
    SYSLOG.register_command_line_monitor()
    SYSLOG.register_file_logger()
    ap = utils.ArgumentParser(usage, utils.get_full_version())
    try:
        options, datasources = \
            ap.parse_args(cliargs, argfile='argumentfile', unescape='escape',
                          help='help', version='version', check_args=True,
                          **argparser_config)
    except Information, msg:
        _exit(INFO_PRINTED, str(msg))
    except DataError, err:
        _exit(DATA_ERROR, str(err))

    try: 
        suite = method(*datasources, **options)
    except DataError:
        _exit(DATA_ERROR, *utils.get_error_details())
    except (KeyboardInterrupt, SystemExit):
        _exit(STOPPED_BY_USER, 'Execution stopped by user.')
    except:
        error, details = utils.get_error_details()
        _exit(FRAMEWORK_ERROR, 'Unexpected error: %s' % error, details) 
    else:
        _exit(suite)

           
def run(*datasources, **options):
    """Executes given Robot data sources with given options.
    
    Data sources are paths to files and directories, similarly as when running
    pybot/jybot from command line. Options are given as keywords arguments and
    their names are same as long command line options without hyphens.
    
    Examples:
    run('/path/to/tests.html')  
    run('/path/to/tests.html', '/path/to/tests2.html', log='mylog.html')
    
    Equivalent command line usage:
    pybot /path/to/tests.html 
    pybot --log mylog.html /path/to/tests.html /path/to/tests2.html
    """
    settings = RobotSettings(options)
    SYSLOG.register_command_line_monitor(settings['MonitorWidth'], 
                                         settings['MonitorColors'])
    output = Output(settings)
    settings.report_possible_errors()
    init_global_variables(settings)
    _syslog_start_info('Robot', datasources, settings)
    suite = TestSuite(datasources, settings)
    suite.run(output)
    SYSLOG.info("Tests executed successfully. Statistics:\n%s" % suite.get_stat_message())
    testoutput = RobotTestOutput(suite, settings)
    output.close1(suite)
    if settings.is_rebot_needed():
        datasources, settings = settings.get_rebot_datasources_and_settings()
        if settings['SplitOutputs'] > 0:
            testoutput = SplitIndexTestOutput(suite, datasources[0], settings)
        else:
            testoutput = RebotTestOutput(datasources, settings)
        testoutput.serialize(settings)
    output.close2()
    return suite


def rebot(*datasources, **options):
    """Creates reports/logs from given Robot output files with given options.
    
    Given input files are paths to Robot output files similarly as when running
    rebot from command line. Options are given as keywords arguments and
    their names are same as long command line options without hyphens.
    
    Examples:
    rebot('/path/to/output.xml')
    rebot('/path/out1.xml', '/path/out2.xml', report='myrep.html', log='NONE')
    
    Equivalent command line usage:
    rebot /path/to/output.xml
    rebot --report myrep.html --log NONE /path/out1.xml /path/out2.xml
    """
    settings = RebotSettings(options)
    SYSLOG.register_command_line_monitor(colors=settings['MonitorColors'])
    settings.report_possible_errors()
    _syslog_start_info('Rebot', datasources, settings)
    testoutput = RebotTestOutput(datasources, settings)
    testoutput.serialize(settings, generator='Rebot')
    SYSLOG.close()
    return testoutput.suite
    
    
def _syslog_start_info(who, sources, settings):
    SYSLOG.info(utils.get_full_version(who))
    SYSLOG.info('Settings:\n%s' % settings)
    SYSLOG.info('Starting processing data source%s %s'
                % (utils.plural_or_not(sources), utils.seq2str(sources)))


def _exit(rc_or_suite, message=None, details=None):
    """Exits with given rc or rc from given output. Syslogs error if given.
    
    Exit code is the number of failed critical tests or error number.
      0       - Tests executed and all critical tests passed
      1-250   - Tests executed but returned number of critical tests failed
                (250 means 250 or more failures)
      251     - Help or version info was printed
      252     - Invalid test data or command line arguments
      253     - Execution stopped by user
      255     - Internal and unexpected error occurred in the framework itself
    """
    if utils.is_integer(rc_or_suite):
        rc = rc_or_suite
        if rc == INFO_PRINTED:
            print message
        else:
            if rc == DATA_ERROR:
                message += '\n\nTry --help for usage information.'
            SYSLOG.error(message)
            if details:
                SYSLOG.info(details)
    else:
        rc = rc_or_suite.critical_stats.failed
        if rc > 250:
            rc = 250
    sys.exit(rc)
