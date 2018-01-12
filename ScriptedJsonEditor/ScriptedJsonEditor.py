# pylint: disable=invalid-name
# Warning		Module name "ScriptedJsonEditor" doesn't conform to snake_case naming style

"""
 Scripted JSON editor to make changes for example to rFactor 2 player.json
 1) Read the file
 2) edit("Graphic Options", "Track Detail", 1)
    Repeat as necessary
 3) Write the file
"""

import json
import os
import sys
from json_include import build_json_include

from backups import Backups
from command_line import CommandLine

BUILD_REVISION = 42 # The git commit count

# User-defined exceptions
class EmptyJsonError(Exception):
  """ The JSON string (usually loaded from a .JSON file) is empty """
  pass

class JsonContentError(Exception):
  """ The JSON string (usually loaded from a .JSON file) is invalid in some way """
  pass

class JobFileFormatError(Exception):
  """ The job file format does not match the program """
  pass

class JobFailedError(Exception):
  """ The job failed to run """
  pass


class JsonFile():
  """
  Read, write and edit a JSON file.
  """
  def __init__(self):
    self.json_dict = None
    self.filename = None
    self.filepath = None
    self.config = {
      "skip keys with # in them": True
    }

  def read(self, filepath, dirPath=None):
    """ Read the JSON file """
    try:
      with open(filepath) as f_p:
        try:
          self.json_dict = json.load(f_p)
          self.filepath = filepath
          return self.json_dict
        except ValueError as err:
          print('JSON content error in "%s"' % filepath)
          print(err)
    except IOError:
      print('Failed to open JSON file "%s"' % filepath)
    raise JsonContentError

  def readInclude(self, filepath, dirpath=None):
    """
    Read the JSON file that may include other JSON files
    (in the same folder unless 'dirpath' is set)
    """
    try:
      if dirpath is None:
        dirpath = os.path.abspath(os.path.dirname(os.path.realpath(filepath)))

      _filepath = os.path.basename(filepath)
      self.json_dict = json.loads(build_json_include(dirpath, _filepath, indent=2))
      self.filepath = filepath
      return self.json_dict
    except ValueError as err:
      print('JSON content error in "%s"' % filepath)
      print(err)
    except IOError:
      print('Failed to open JSON file "%s"' % filepath)
    else:
      raise
    raise JsonContentError

  def write(self, _filepath=None):
    """ Write the JSON file
    _filepath is for unit testing
    """
    _json_txt = json.dumps(self.json_dict, indent=2)
    self._write_json_text(_json_txt, _filepath)

  def _write_json_text(self, json_txt, filepath=None):
    if filepath is None:
      filepath = self.filepath
    with open(filepath, 'w') as f_p:
      try:
        f_p.write(json_txt)
      except IOError:
        print('Failed to write JSON file "%s"' % filepath)
        # ToDo: restore back up?

  def edit(self, main_key, sub_key, new_value):
    """
    Change the value of 'main_key''sub_key' in the JSON file to 'new_value'
    May raise KeyError, ValueError or EmptyJsonError
    """
    if self.json_dict is None:
      print('Empty JSON file "%s"' % self.filepath)
      raise EmptyJsonError

    if '#' in sub_key and self.config["skip keys with # in them"]:
      pass # it's a "comment main_key"
    else:
      # check that key exists, otherwise it's a typo in the job
      if main_key in self.json_dict:
        if sub_key in self.json_dict[main_key]:
          try:
            self.json_dict[main_key][sub_key] = new_value
          except ValueError:
            try:
              print('Invalid value "%s" in "%s":"%s"' % (new_value, main_key, sub_key))
            except ValueError:
              print('Invalid number %d in "%s":"%s"' % (new_value, main_key, sub_key))
            raise ValueError
          else:
            pass #what?
        else:
          print('No existing sub key "%s" in main key "%s"' % (sub_key, main_key))
          raise KeyError
      else:
        print('No existing main key "%s":"%s"' % (main_key, sub_key))
        raise KeyError

  def _load(self, json_str, string_name):
    """
    For unit tests - load the JSON dict with a string giving values to be edited.
    Use the string name as a dummy filename
    """
    try:
      self.json_dict = json.loads(json_str)
      self.filename = string_name
      return self.json_dict
    except ValueError:
      print('JSON string content error in _load()')
      raise ValueError

  def _get_value(self, main_key, sub_key):
    """ For unit tests - get value of dict key """
     # pylint: disable=no-else-return
    if main_key in self.json_dict:
      if sub_key in self.json_dict[main_key]:
        return self.json_dict[main_key][sub_key]
      else:
        print('Sub key "%s" not in main key "%s"' % (sub_key, main_key))
        return None
    else:
      print('Main key "%s" not in JSON dict' % main_key)
      return None

class JsonJobsFile(JsonFile):
  """
  Get a list of keys in the item "jobs".
  """
  def __init__(self):
    # default to rfactor 2 player.json filepath and formatting:
    super().__init__()
    self.config = \
      {"JSONfileToBeEdited":
       r"c:\Program Files (x86)\Steam\steamapps\common\rFactor 2\UserData\player\player.JSON",
       "<PLAYER.JSON>":
       r"c:\Program Files (x86)\Steam\steamapps\common\rFactor 2\UserData\player\player.JSON",
       "<CONTROLLER.JSON>":
       r"c:\Program Files (x86)\Steam\steamapps\common\rFactor 2\UserData\player\controller.JSON",
       "skip keys with # in them": True,
       "rFactor escape slash": True
      }

  def read(self, filepath, dirpath=None):
    self.json_dict = super().read(filepath)
    return self._read()

  def _read(self):
    """ accessed directly by unit tests """
    try:
      self.json_dict["jobs file format"] == 6
    except (KeyError, AssertionError):
      print('Warning: %s "jobs file format" should be 6' % self.filepath)
      #raise JobFileFormatError
    if self.json_dict:
      for key in ["JSONfileToBeEdited",
                  "<PLAYER.JSON>",
                  "<CONTROLLER.JSON>",
                  "skip keys with # in them",
                  "rFactor escape slash"]:
        if key in self.json_dict:
          self.config[key] = self.json_dict[key]
    return self.json_dict, self.config

  def get_jobs(self):
    """
    Get the list of jobs in this JSON dict,
    each one a (job definition file, job) tuple
    """
    _job_definitions = {}
    _result = []
    try:
      for _job_description_file in self.json_dict["job definition files"]:
        _JDFO = JsonJobsDefinitionsFile(self.config)
        try:
          _JDFO.read(_job_description_file)
          _job_definitions[_JDFO.get_filename()] = _JDFO
        except:
          raise
      for _job_definition_file_set in self.json_dict["jobs"]:
        for _job_definition_file in _job_definition_file_set:
          for _job in _job_definition_file_set[_job_definition_file]:
            _result.append(_job_definitions[_job_definition_file].get_job(_job))
    except KeyError:
      print('%s has no "job definition files"' % self.filepath)
    return _result

class JsonJobsDefinitionsFile(JsonFile):
  """
  Get a list of job definitions.
  Substitute any macro definitions from the config provided.
  """
  def __init__(self, config):
    super().__init__()
    self.config = config
    self.filename = None
    self.filepath = None

  def read(self, filepath, dirpath=None):
    self.json_dict = super().read(filepath)
    # Extract filename (without extension) used to fully specify jobs
    self.filepath = os.path.basename(filepath)
    self.filename, _ = os.path.splitext(self.filepath)
    return self._read()

  def _read(self):
    try:
      json_dict = self.json_dict["job definitions"]
    except:
      print('"job definitions" absent from %s' % self.filepath)
      raise JsonContentError
    for job in json_dict:
      try:
        if json_dict[job]["JSONfileToBeEdited"] in self.config:
          # substitute the macro
          json_dict[job]["JSONfileToBeEdited"] = self.config[json_dict[job]["JSONfileToBeEdited"]]
      except KeyError:
        print('"JSONfileToBeEdited" not in %s job "%s"' % (self.filepath, job))
        raise JsonContentError
    this_file_dict = {self.filename: json_dict}
    return this_file_dict

  def get_filename(self):
    """ get filename (without extension) """
    return self.filename

  def get_job(self, job_name):
    """ get the job 'job_name' """
    try:
      return self.json_dict['job definitions'][job_name]
    except KeyError:
      print('No job "%s" in %s' % (job_name, self.filepath))
      return None

class JsonRfactorFile(JsonFile):
  """
  Use rfactor 2 player.json formatting:
  """
  def write(self, _filepath=None):
    """ Write the JSON file, maintaining the rFactor 2 JSON "style"
    _filepath is for unit testing
    """
    if _filepath is None:
      _filepath = self.filepath
    _json_txt = json.dumps(self.json_dict, indent=2).splitlines()
    # json.dumps() puts a space bwetween :{  rF2 doesn't
    # So strip it out to make it easier to compare before and after
    _whitespace_removed = []
    for _line in _json_txt:
      _line = _line.replace(': {', ':{', 1)

      # For some reason rF2 escapes / in values
      _colon = _line.find(':')
      if _colon:
        _line = _line[:_colon] + _line[_colon:].replace('/', r'\/')
      _whitespace_removed.append(_line)
    _json_txt = '\n'.join(_whitespace_removed)

    super()._write_json_text(_json_txt, _filepath)

class Job():
  """ Run a job """
  def __init__(self, job, config):
    self.job = job
    self.config = config
    if self.config['rFactor escape slash']:
      self.json_o = JsonRfactorFile()
    else:
      self.json_o = JsonFile()

  def read_json_file_to_be_edited(self):
    """
    Read the file specified by the job file key 'JSONfileToBeEdited'
    May raise JsonContentError
    """
    _json_file = self.job["JSONfileToBeEdited"]
    if _json_file in self.config:
      # Substitute the path defined in the macro
      _json_file = self.config[_json_file]
    self.json_o.read(_json_file)

  def _load(self, json_str, filepath):
    """ For unit tests - load the JSON dict with values to be edited """
    # pylint: disable=protected-access
    return self.json_o._load(json_str, filepath)

  def _get_value(self, main_key, sub_key):
    # pylint: disable=protected-access
    return self.json_o._get_value(main_key, sub_key)

  def run_edits(self):
    """
    Execute the job's edits on current file
    May raise KeyError or ValueError
    """
    for main_key in self.job["edits"]:
      for _item in self.job["edits"][main_key]:
        self.json_o.edit(main_key, _item, self.job["edits"][main_key][_item])

  def backup_file(self):
    """ Move file to datestamped file in temp folder """
    _backupO = Backups()
    _backupFilename = _backupO.backup_file(self.job["JSONfileToBeEdited"])
    return 'Original file %s backed up to %s' % (self.job["JSONfileToBeEdited"], _backupFilename)

  def write(self):
    """ Write the edited file """
    self.json_o.write()

#####################################################

def read_jobs_file(jobs_file_name):
  """
  Read the jobs file. Return
  * the config
  * the list of job definition file, job name pairs
  """
  _JSNO_O = JsonJobsFile()
  __, config = _JSNO_O.read(jobs_file_name)
  _jobs = _JSNO_O.get_jobs()
  return config, _jobs

def run_job(job, config):
  """
  Run the job, editing the file and backing it up.
  Return status report string.
  Exceptions:
  * JobFailedError    could not execute the job
  * FileNotFoundError could not open the file to edit
  """
  _j = Job(job, config)
  #   read the file to be edited
  try:
    _j.read_json_file_to_be_edited()
    #   do the edits
    try:
      _j.run_edits()
      #   if successful:
      #     backup 'filepath'
      #     save new contents to 'filepath
      _report = _j.backup_file()
      _j.write()
      return _report
    except (KeyError, ValueError, EmptyJsonError):
      raise JobFailedError
  except JsonContentError:
    raise FileNotFoundError

def main():
  """ Main """
  _clo = CommandLine()
  jobs_file_name = _clo.get_jobs_file()
  if jobs_file_name is None:
    # No jobs file in command line
    return 1

  try:
    _JSNO_O = JsonJobsFile()
    __, config = _JSNO_O.read(jobs_file_name)
    _jobs = _JSNO_O.get_jobs()
  except JsonContentError:
    return 99

  if _jobs is None:
    print('No jobs in"%s"' % jobs_file_name)
    return 99

  # Execute
  # For each job in jobsFile
  for job in _jobs:
    try:
      _report = run_job(job, config)
      print(_report)
    except JobFailedError: # failed to execute job
      return 98
    except FileNotFoundError:
      print('Failed opening "%s"' % (job['JSONfileToBeEdited']))
      return 99
  return 0

if __name__ == '__main__':
  print('Scripted JSON Editor V0.6.%d\n' % BUILD_REVISION)
  _result = main()
  sys.exit(_result)
