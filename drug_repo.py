# Copyright 2014 Sandra Giuliani
# drug_repo.py

# Mapping of known drugs from ChEMBL and DrugBank to their targets/domain
# architecture to identify suitable drug repositioning candidates for
# schistosomiasis.
# Please see README.md for more info.


############################################################################
### import modules, set up logger
############################################################################

# import os (old system)
import os
# os system does not work very well, it is deprecated, use subprocess
#os.system('./../archSchema/bin/archindex -u B6DTB2 > test2.txt')

# import os.path for checking if files exist
import os.path

# import pickle
#import pickle

# cpickle
import cPickle as pickle

# import csv for comma-sep files
import csv

# import subprocess for executing command line
import subprocess

# import itertools for flatten out lists
import itertools

# izip_longest to split dictionaries into chunks (part 8)
from itertools import izip_longest

# import other modules
import sys, re, string, fnmatch, shutil

# import Biopython Entrez
from Bio import Entrez
# tell NCBI who I am
Entrez.email = "sandraxgiuliani@gmail.com"

# import SeqIO
from Bio import SeqIO

# list available databases
#handle = Entrez.einfo()
#logger.info(handle.read())

# import expasy for access protein sequences
from Bio import ExPASy

# import swissprot for parsing swissprot plain text files
from Bio import SwissProt

# for http
from urllib2 import urlopen, HTTPError
#import urllib2

# linecache for jumping to specific lines
import linecache

# datetime
from datetime import datetime

# set up log
import logging
# set up log file to write to, it will be overwritten every time ('w' mode)
# leave this level setting to DEBUG
logging.basicConfig(filename='log_drug_repo.log', filemode='w',
                    level=logging.DEBUG)
logger = logging.getLogger(__name__)
# leave this level setting to DEBUG
logger.setLevel(logging.DEBUG)
# create console handler
ch = logging.StreamHandler()
# CHANGE THIS TO TUNE LOGGING LEVEL from DEBUG/INFO/WARNING
ch.setLevel(logging.INFO)
# create formatter, you can add:
# '%(levelname)s' for level eg DEBUG, INFO..
# '%(name)s' for level name, eg __main__ in the log
formatter = logging.Formatter('%(asctime)s - %(message)s')
# add formatter to ch
ch.setFormatter(formatter)
# add ch to logger
logger.addHandler(ch)

# autovivification for creating nested dictionaries automatically
class AutoVivification(dict):
  """Implementation of perl's autovivification feature."""
  def __getitem__(self, item):
      try:
          return dict.__getitem__(self, item)
      except KeyError:
          value = self[item] = type(self)()
          return value
############################################################################




############################################################################
### define global variables
############################################################################

# define CHEMBL_INPUT as the drug file from ChEMBL ('Browse drugs')
# 'chembl_drugs.txt'
# number of drugs should be 10406
CHEMBL_INPUT = 'chembl_drugs.txt'

# define CHEMBL_TARGETS as the target file from ChEMBL ('Browse drug targets')
# number of drugs associated with targets should be 2007
CHEMBL_TARGETS = 'chembl_drugtargets.txt'

# define CHEMBL_UNIPROT as the chemblID/uniprot mapping file
CHEMBL_UNIPROT = 'chembl_uniprot_mapping.txt'

# define list of clinical phases we are interested
# eg. '4', '3', '' (empty string for the unknown phase)
CHEMBL_CLINICAL_PHASES = ['4']

# define molecule types we are interested in
CHEMBL_MOL_TYPE = ['Synthetic Small Molecule']

# define DRUGBANK_INPUT as the DrugBank Drug Target Identifiers
# either: all_target_ids_all.csv (all drugs, 4,026 entries),
# or: small_molecule_target_ids_all.csv (small molecule drugs, 3,899 entries)
DRUGBANK_INPUT = 'small_molecule_target_ids_all.csv'

# define sdf file with drugbank drugs (contains smiles)
DRUGBANK_SDF = 'all.sdf'

# define TAXA as the list of taxonomy identifiers we are interested in
# e.g. SCHMA (S. Mansoni), SCHHA (S. haematobium), SCHJA (S. japonicum)
TAXA = ['SCHMA', 'SCHHA', 'SCHJA']

# format of CATH domain eg '4.10.400.10'
CATH_FORMAT = re.compile('.*\..*\..*\..*')

# path to archindex binary
# old path "./../archSchema/bin/archindex" still valid on mac
# new path on linux machine "./../Arch/archindex"
ARCHINDEX_PATH = "./../Arch/archindex"

# uniprot to pdb csv mapping file - can also use the .tsv version if easier
UNIPROT_PDB = "uniprot_pdb.csv"

# pdb to het mapping file, contains all het groups
PDB_HET = "het_pairs.lst"

# pdb to lig mapping file
PDB_LIG = "lig_pairs.lst"

# csv containing list of xtal het groups (ligands) we are not interested in
# here below one of methods to manually add up eg short het groups
  # thingo = []
  # logger.debug(len(cc_smi_filt))
  # for thing in cc_smi_filt:
  #   #logger.debug(thing)
  #   if len(cc_smi_filt[thing]) < 5:
  #     thingo.append(thing)
  # logger.debug(thingo)

POINTLESS_HET = "pointless_het.csv"

# regular expression for string containing at least one dash
CONTAINS_DASH = re.compile('.*-.*')

# regular expression for string containing at least one '#'
CONTAINS_COMMENT = re.compile('#.*')

# chemical component smiles dictionary
CC_SMI = "Components-smiles-oe.smi"

# absolute path to SMSD directory (where SMSD.sh is)
# 1.5.1 - first version I have used (from sourceforge)
# 1.6 - version sent by Asad that should handle multiple sdf and keep ids
SMSD_PATH = "/home/sandra/SMSD1.6"

# similarity threshold for clustering
SIM_THRESHOLD = 0.9
# check if float
#logger.info(isinstance(SIM_THRESHOLD, float))

# path to run modeller in (where input files are) and dump output here
MODELLER_PATH = "/home/sandra/alignments"

############################################################################




############################################################################
### HEADER_COUNT HELPER FUNCTION
############################################################################
# find specific header in line of comma or tab (or other) separated
# file and return column number of the header
def header_count(line, separator, header):
  '''
  Read a string (line) separated by separator
  and return column number of a specific string (header)
  '''
  #set counter to 0
  col_number = 0
  # loop until word matches the header
  while not line.split(separator)[col_number].rstrip('\r\n') == header:
    col_number = col_number + 1
  # return column number
  return col_number
############################################################################



############################################################################
### FILE_TO_LINES HELPER FUNCTION
############################################################################
# read file using readlines approach and return the lines
def file_to_lines(text_file):
  try:
    input_file = open(text_file, 'r')
    lines = input_file.readlines()
    input_file.close()
    #logger.debug('the try/expect loop is working')
    return lines
  except IOError:
    logger.error('The file ' + text_file + ' cannot be found' +
                 ' in the current directory!')
    #this logger exception will print the whole thing
    #logger.exception('whaaaaat we have error')
    logger.warning('The program is aborted.')
    # exit python
    sys.exit()
############################################################################




############################################################################
### SWAP_DIC HELPER FUNCTION
############################################################################
# read tab-separated mapping file with header and return dictionary with
# second column as key and first column as values - created for the
# chemblID uniprot mapping file
def swap_dic(tab_file):
  lines = file_to_lines(tab_file)
  swap_dictionary = {}
  counter = 0
  # iterate over lines
  for i in range(1,len(lines)):
    # split tab
    splitline = lines[i].split("\t")
    counter = counter + 1
    #logger.debug(splitline[0])
    # create dictionary, stripping the carriage return
    swap_dictionary[splitline[1].rstrip('\r\n')] = (splitline[0])
  #logger.debug(swap_dictionary)
  return swap_dictionary
############################################################################



############################################################################
### PROCESS_CHEMBL FUNCTION
############################################################################

# in the end we need a dictionary of chembl ids vs uniprot ids
def process_chembl(input_file):
  # open chembldrugs.txt for reading
  lines = file_to_lines(input_file)
  # logger.info('The ChEMBL input file contains a total of '
  #             + str(len(lines)-1) + ' drugs.')

  ### ANALYSE HEADERS AND OBTAIN COLUMN NUMBERS

  # get the headers
  headers = lines[0]
  # remove duplicate spaces
  #headersnospace = " ".join(headers.split())
  # print headers list in lowercase
  # print('The headers are: '+headersnospace.lower())

  col_phase = header_count(headers, "\t", "DEVELOPMENT_PHASE")
  col_type = header_count(headers, "\t", "DRUG_TYPE")
  col_chemblid = header_count(headers, "\t", "CHEMBL_ID")

  # count the drugs in the 4+1 classes of clinical phase
  # set counters for clinical phases to zero
  phase1 = 0
  phase2 = 0
  phase3 = 0
  phase4 = 0
  phase_unknown =0
  # iterate over rows, excluding the header row
  for i in range(1,len(lines)):
    # tab separate each row
    rowsplit = lines[i].split("\t")
    if (rowsplit[col_phase] == '1'):
      phase1 = phase1 + 1
    elif (rowsplit[col_phase] == '2'):
      phase2 = phase2 + 1
    elif (rowsplit[col_phase] == '3'):
      phase3 = phase3 + 1
    elif (rowsplit[col_phase] == '4'):
      phase4 = phase4 + 1
    else:
      phase_unknown = phase_unknown + 1

  # logger.info('The number of drugs in phase 1 is: ' + str(phase1) +
  #             '; in phase 2 is: ' + str(phase2) + '; in phase 3 is: ' +
  #             str(phase3)+'; in phase 4 is: ' + str(phase4) +
  #             '; in unknown phase is: ' + str(phase_unknown) + '.')
  ###


  ### CLINICAL PHASE AND MOLECULAR TYPE FILTER
  # IN THE END WE OBTAIN CHEMBL_FILT_LIST THAT HAD THE FILTERED CHEMBL IDS
  # possibly merge THEM TOGETHER!

  # set up empty list to append lines to
  stripped = []
  # look over lines, excluding header
  for y in range(1,len(lines)):
    # tab separate each row
    rowsplit2 = lines[y].split("\t")
    # check if they are in clinical phase we are intereste in
    if (rowsplit2[col_phase] in CHEMBL_CLINICAL_PHASES):
      # append the stripped lines to the list
      stripped.append(lines[y])

  # empty list in which to store filtered chembl drug ids
  chembl_filt_list = []
  # loop over, note here there is no header
  for line in stripped:
    # tab separate
    rowsplit3 = line.split("\t")
    # check if they are of the desired drug type
    if rowsplit3[col_type] in CHEMBL_MOL_TYPE:
      #logger.debug(rowsplit3[col_chemblid])

      # make list of chembl ids we are interested in
      chembl_filt_list.append(rowsplit3[col_chemblid])

  logger.info('We have filtered the entries in clinical phases ' +
              str(CHEMBL_CLINICAL_PHASES) + ' and of molecule type ' +
              str(CHEMBL_MOL_TYPE) + ', to obtain ' +
              str(len(chembl_filt_list)) + ' drugs.')
  ###


  # CREATE DICTIONARY CHEMBL_TARGET_DRUG_DIC IN WHICH TO STORE
  # {CHEMBL TARGET IDS: (LIST OF CHEMBL DRUG IDS)}

  # open the drug targets chembl file and get lines
  drug_targ = file_to_lines(CHEMBL_TARGETS)
  # get column number for two headers we want (chembl ids for mol and targets)
  col_mol_id = header_count(drug_targ[0], '\t', 'MOLECULE_CHEMBL_ID')
  col_targ_id = header_count(drug_targ[0], '\t', 'TARGET_CHEMBL_ID')
  #logger.debug(col_targ_id)

  # empty dictionary
  chembl_target_drug_dic = {}

  # list of target chemblids that refer to the drugs we are interested in
  # ie. small molecules, late clinical stages
  for i in range(1,len(drug_targ)):
    rowsplit = drug_targ[i].split("\t")
    #logger.debug(rowsplit)

    # get the chembl drug and target id values for the row
    chembl_drug_id = rowsplit[col_mol_id]
    chembl_target_id = rowsplit[col_targ_id]

    # only proceed if the target id is not an empty field!
    if chembl_target_id  != "":

      # check if the molecule chembl id is one of the drugs we want
      if chembl_drug_id in chembl_filt_list:

        # check if the target is is already in the dictionary, and extend
        if chembl_target_id in chembl_target_drug_dic:
          # try to append stuff to dictionary
          chembl_target_drug_dic[chembl_target_id].append(chembl_drug_id)

        # else create the new entry in the dictionary
        else:
          # create empty list
          chembl_target_drug_dic[chembl_target_id] = []
          # append to empty list the value
          chembl_target_drug_dic[chembl_target_id].append(chembl_drug_id)

  # test to see if there are duplicates drugs
  # positive: tot 2007 but 1596 unique
  #logger.debug(len(test_duplo))
  #logger.debug(len(list(set(test_duplo))))

  # number of drugs we could associate with chembl target
  # this will be a list of lists, so we need to flatten it out
  drug_ids = list(itertools.chain(*list(chembl_target_drug_dic.values())))
  #logger.debug(len(drug_ids))

  # eliminate duplicates
  drug_ids = list(set(drug_ids))
  #logger.debug(drug_ids)

  ###


  # create dictionary from the chembl/uniprot mapping file
  # the dictionary will be {'chemblID1':'uniprotid1', etc..}
  # the dictionary has to be this way because more than one chembl id
  # can point to the same uniprot id
  chembl_uniprot_map_dic = swap_dic(CHEMBL_UNIPROT)
  #logger.debug(chembl_uniprot_map_dic)

  # compare length dictionary with unique uniprot id values!
  #logger.debug(len(chembl_uniprot_map_dic))
  #logger.debug(len(list(set(chembl_uniprot_map_dic.values()))))


  # empty dictionary,it will store {drug chembl id : [list of uniprot]}
  chembl_dic = {}

  # new method to create swap dictionary instead!
  # loop over unique list of drug ids
  for drug in drug_ids:
    # empty target list in which to store target ids
    target_list = []
    # loop over dictionary of chembl target ids and drug chembl ids
    for key in chembl_target_drug_dic:
      # check if drug is in the list
      if drug in chembl_target_drug_dic[key]:
        # append chembl id to list
        target_list.append(key)
    #logger.debug(target_list)

    # empty list for uniprot values
    uniprot_list = []
    # loop over the list of chembl ids we have just generated
    for chembl_id in target_list:
      # check if this id is in the mapping dictionary
      if chembl_id in chembl_uniprot_map_dic:
        # append uniprot value to list
        uniprot_list.append(chembl_uniprot_map_dic[chembl_id])

    # check the list is not empty
    if uniprot_list != []:
      chembl_dic[drug] = uniprot_list

  # return dictionary {uniprot1:(list of chembl ids)}
  return chembl_dic
############################################################################




############################################################################
### PROCESS_DRUGBANK FUNCTION
############################################################################
# process drugbank file, return a dictionary of drugs vs uniprot ids. Deal
# with duplicate values and append to list in the dictionary.
def process_drugbank(input_file):

  # open and read drug_bank input and count number
  lines = file_to_lines(input_file)
  # number of entries (remember there is header)
  # logger.info('The DrugBank input file contains ' + str(len(lines)-1) +
  #             ' entries.')

  # headers are first line of the file, stripped of carriage return
  headers = lines[0].rstrip('\r\n')
  #logger.debug('The DrugBank headers are: ' + headers + '.')
  # find column number of uniprot and drugbank ids
  col_uniprot = header_count(headers, "," , "UniProt ID")
  col_drugbankids = header_count(headers, "," , "Drug IDs")
  #logger.debug(col_uniprot)
  #logger.debug(col_drugbankids)

  # empty dictionary in which to store drugbank info
  drugbank_dic = {}
  # loop over to len(lines), excluding first line (headers)
  #for i in range(1,3898):
    #logger.debug(lines[i])
    # do I need here skipinitialspace=True ??

  # read csv lines with the csv reader - deals with quotation marks etc..
  incsv = csv.reader(lines)
  # skip the first line with the headers
  next(incsv)
  # loop over each line
  for line in incsv:
    #list_check.append(line[col_uniprot])
    drug_string = line[col_drugbankids]
      # list of drubbank ids
    drug_split = drug_string.split(';')
    #ogger.debug(drug_split)
      # check if uniprot id is already in the dictionary
    if line[col_uniprot] in drugbank_dic:
      # append drug id value to the list in the dictionary
      # the '.extend' prevents the formation of a list of lists!
      drugbank_dic[line[col_uniprot]].extend(drug_split)
    else:
      # populate dictionary with the new entry
      drugbank_dic[line[col_uniprot]] = drug_split

  # confirm we are dealing with duplicates
  #logger.debug(len(list_check))
  #logger.debug(len(list(set(list_check))))


  # fast and silly way to generate the swap dictionary!

  drugbank_list = list(itertools.chain(*list(drugbank_dic.values())))
  drugbank_unique = list(set(drugbank_list))

  #logger.debug(len(drugbank_unique))



  drugbank_swap = {}

  # loop over list of unique drugbank ids
  for drug in drugbank_unique:
    #empty list for the uniprot values
    uniprot_list = []
    for uniprot in drugbank_dic:
      for db in drugbank_dic[uniprot]:
        if db == drug:
          # append uniprot value to the list
          uniprot_list.append(uniprot)

    # sanity check the list is not empty
    if uniprot_list:
    # the list is now ready, populate the dictionary
      drugbank_swap[drug] = uniprot_list



  #logger.debug(drugbank_swap)

  # return dictionary {uniprot1:(list of drugbank ids)}
  return drugbank_swap
############################################################################




############################################################################
### UNIPROT_TO_ARCH FUNCTION
############################################################################
def uniprot_to_arch(uniprot_list,architecture):
  ''' run archindex, return dictionary of CATH/pfam domain architecture vs
   uniprot values
  '''
  if architecture == "cath":
    flag = "-cath"

  elif architecture == "pfam":
    flag = ""

  # dictionary of uniprot ids and list of correposponding architectures
  arch_dic = {}

  # loop over list of uniprot values
  for uniprot_id in uniprot_list:
    #list in which to store list of CATH domains for each entry
    architect_list = []
    # call archschema on the list
    subprocess.call(ARCHINDEX_PATH + " -u " + str(uniprot_id) +
                  " -maxa 1 -maxs 1 " + str(flag) +" > temp.txt", shell=True)
    # store lines
    lines = file_to_lines('temp.txt')
    #logger.debug(lines)
    for i in range(len(lines)):
      # find line that starts with parent
      if lines[i][0:7] == ':PARENT':
        # take the line after the ':PARENT' and split it
        line_split = lines[i+1].split("\t")
        #logger.debug('the line after is ' + str(line_split))


        ### for cath ###
        if architecture == "cath":

          # check if there are 'p's and get rid of them
          if "p" in line_split[2]:
            # replace p's with nothing
            line_nops = line_split[2].replace('p','')
          else:
            line_nops = line_split[2]

          # check if there are undescores
          if "_" in line_nops:
            undersc_split = line_nops.split("_")
            #logger.debug(undersc_split)

            for item in undersc_split:
              # check if the format is CATH one
              #cath_format = re.compile('.*\..*\..*\..*')
              if CATH_FORMAT.match(item):
                architect_list.append(item)

          # this is the case of just one entry, no undescores
          else:
            # check the format is CATH one
            if CATH_FORMAT.match(line_nops):
              architect_list.append(line_nops)


        ### for pfam ###
        elif architecture == "pfam":
          # check if there are dots
          if "." in line_split[2]:
            dot_split = line_split[2].split(".")
            #logger.debug(undersc_split)

            for item in dot_split:

              architect_list.append(item)

          # this is the case of just one entry, no dots
          else:
            architect_list.append(line_split[2])


    # check list is not empty
    if architect_list:

      # eliminate duplicates within the list (this is for each entry!!)
      architect_list = list(set(architect_list))

      # populate the dictionary
      arch_dic[uniprot_id] = architect_list

  #logger.debug(cath_dic)

  # rm temp.txt in the end
  # this is the last temp file that overwrote the others
  subprocess.call("rm temp.txt", shell=True)

  #logger.info('We have found ' + str(len(architect_list)) +
  #            ' unique CATH domain architectures.')

  #logger.debug(architect_list)
  # return the list of unique domain architecture values
  return arch_dic
############################################################################




############################################################################
### ARCH_TO_UNIPROT FUNCTION
############################################################################
# run archindex, filter for TAXA and find uniprot ids
def arch_to_uniprot(arch_list,architecture):
  '''(list of str -> list of str)
  run archindex, return dictionary of uniprot from list of domain
  architecture values applying a filter for TAXA (organism)
  '''

  if architecture == "cath":
    flag = "-cath"
  elif architecture == "pfam":
    flag = ""

  # empty dictionary
  uniprot_dic = {}
  # loop over list of arch values
  for arch_id in arch_list:
    # empty list in which to store uniprot values
    uniprot_list = []
    # iterate over the taxa code list (schisto species)
    for taxa_code in TAXA:
      # call archschema on the list
      subprocess.call(ARCHINDEX_PATH + " -p " + str(arch_id) +
                    " -maxa 1 -maxs 1 " + str(flag) + " -s " + taxa_code +
                    " > temp.txt", shell=True)
      # store lines
      lines = file_to_lines('temp.txt')
      #logger.debug(temp.txt)

      # get the uniprot values and append them to uniprot_list
      for i in range(len(lines)):
        # find line that starts with parent
        if lines[i][0:7] == ':PARENT':
          # take the line after the ':PARENT' and split it
          line_split = lines[i+1].split("\t")

          uniprot_list.append(line_split[0])

    # check list is not empty
    if uniprot_list:
      # remove duplicates from list
      uniprot_list = list(set(uniprot_list))

      # populate the dictionary
      uniprot_dic[arch_id] = uniprot_list

  # rm temp.txt in the end
  # this is the last temp file that overwrote the others
  subprocess.call("rm temp.txt", shell=True)

  #logger.info('Using ' + str(architecture) +
  #            ' domain architectures we have found ' +
   #           str(len(uniprot_list)) +
   #           ' UniProt IDs of schistosoma proteins (taxonomic ids ' +
   #            str(TAXA) + ').')


  #return the dictionary
  return uniprot_dic
############################################################################




############################################################################
### MERGE_LISTS
############################################################################
# merge lists, remove duplicates and return merged list
def merge_lists(list1, list2):

  merged_list = list(set(list1)|set(list2))

  #pickle.dump(uniprot_schisto_list, open("uniprot_schisto_list.p", "wb"))

  #logger.debug('The merged UniProt values obtained from CATH and pfam ' +
  #  'are ' + str(len(merged_list)) + '.')

  #logger.debug(uniprot_schisto_list)

  return merged_list
############################################################################




############################################################################
### EXPASY_FILTER
############################################################################
# take list of uniprot, call expasy and applies filter to find the reviewed
# entries

  # entrez fetch does not seem to handle non-swissprot ids (TrEMBL)
  #prothandle = Entrez.efetch(
  #                  db="protein", id= 'P13566', rettype = "gb")
  #seq_record = SeqIO.read(prothandle, "gb")
  #logger.debug(seq_record)

def expasy_filter(uniprot_list, filter_type):
# filter_type == 'reviewed' if you want to keep only reviewed uniprots
# filter_type == 'pdb' if you want to keep only the ones with pdb structures

# alternative to swissport read, should also work
#record = SeqIO.read(handle, "swiss")


    #if len(record.accessions) > 1:
    #  mult_count = mult_count + 1
    #  logger.debug('The entry ' + entry + ' has multiple entries ' +
    #                str(record.accessions))

    #print(record.seqinfo)
    #for ref in record.references:
    #  print(ref.authors)


  # empty list to store filtered entries
  filtered_list = []

  # counter for obsolete/http err
  obsolete = 0

  for entry in uniprot_list:
    try:
        # get handle
        handle = ExPASy.get_sprot_raw(entry)
        # swissprot read
        record = SwissProt.read(handle)
        

        # FILTER according to presence pdb structure
        if filter_type == 'pdb':
          #logger.debug(record.cross_references)
          #so far the pdb does not exist
          pdb_exists = False 

          # get tuples with references (pdb, etc...)
          cross_ref = record.cross_references
          # loop over every tuple in the list
          for tup in record.cross_references:
            # if the first is pdb means there one or more pdb
            if tup[0] == "PDB":
              pdb_exists = True 

          if pdb_exists == True:
            # add entry to the list
            filtered_list.append(entry)


        # FILTER according to reviewed uniprot
        elif filter_type == 'reviewed':
          # check it is reviewed
          if record.data_class == 'Reviewed':
            # add reviewed entry to the list
            filtered_list.append(entry)


    except HTTPError:
      obsolete = obsolete + 1
      #logger.debug('uh-ho')


  logger.debug(obsolete)
  return filtered_list
  #logger.info('The entries with multiple ids are ' + str(mult_count) + '.')

############################################################################




############################################################################
### FLATTEN_DIC
############################################################################
# list from dictionary's key OR values and flatten it 
# for the values, flatten list (from list of lists to simple list) 
# also eliminate duplicates and sort

def flatten_dic(dic, keys_or_val):
  # generate list from values
  if keys_or_val == "values":
    # generate list and flatten it
    flat_list = list(itertools.chain(*list(dic.values())))
  # generate list from keys
  elif keys_or_val == "keys":
    flat_list = dic.keys()


  # rm duplicates
  flat_list = list(set(flat_list))

  #rm white spaces
  flat_list = [x.strip(' ') for x in flat_list]

  flat_list.sort()

  return flat_list
############################################################################




############################################################################
### CHEMBL_REPO
############################################################################
# make big map for chembl ids, for both cath and pfam arch
# format {drug1:{drug_target1:{arch1:[list os schisto uniprot], arch2:[..]},
#                 drug_target2:{..}, drug2:{........}}}

# takes chembl to uniprot dic, uniprot to cath dic, cath to schisto dic,
# uniprot to pfam dic, pfam to schisto dic

def chembl_repo(chembl_dic, cath_dic, schisto_cath_dic,
                    pfam_dic, schisto_pfam_dic):

  # autovivification nested dictionary
  chembl_repo_map = AutoVivification()

  # loop over each drug in the dictionary
  for drug in chembl_dic:

    # dictionary for each drug
    each_drug_dic = {}

    # sanity check the uniprot list is not empty (it should not be empty)
    if chembl_dic[drug]:
      # loop on list of uniprot
      for target in chembl_dic[drug]:

        # make list in which to store the cath/pfam
        cath_pfam = []

        # append cath value, only if it exists in the dictionary
        if target in cath_dic:
          cath_pfam.extend(cath_dic[target])

        # append pfam value, only if it exists in the dictionary
        if target in pfam_dic:
          cath_pfam.extend(pfam_dic[target])

        #logger.debug(cath_pfam)
        # check the list is not empy
        if cath_pfam:
        # make dictionary
          each_drug_dic[target] = cath_pfam

      # finished loops for all targets, we have the dictionary
      # with {uniprot1:[list of arch],uniprot2:[list]}
      #logger.debug(each_drug_dic)

      #loop over each uniprot in new dictionary
      for targ in each_drug_dic:

        # dictionary for each target
        each_target_dic = {}
        # sanity check the arch list is not empty:
        if each_drug_dic[targ]:
          # loop over list of architectures
          for arch in each_drug_dic[targ]:
            # empty list for schisto
            schisto_list = []
            # check it exists in the cath dictionary
            if arch in schisto_cath_dic:
              schisto_list.extend(schisto_cath_dic[arch])

            if arch in schisto_pfam_dic:
              schisto_list.extend(schisto_pfam_dic[arch])



            # check list is not empty
            if schisto_list:
              #logger.debug(schisto_list)
              # add list as values in dictionary
              each_target_dic[arch] = schisto_list

              #logger.debug(each_target_dic)


              chembl_repo_map[drug][targ][arch] = each_target_dic[arch]


  return chembl_repo_map
############################################################################




############################################################################
### DRUGBANK_REPO
############################################################################
# make big map for drugbank ids, for both cath and pfam arch
# format {drug1:{drug_target1:{arch1:[list os schisto uniprot], arch2:[..]},
#                 drug_target2:{..}, drug2:{........}}}

# takes chembl to uniprot dic, uniprot to cath dic, cath to schisto dic,
# uniprot to pfam dic, pfam to schisto dic

def drugbank_repo(drugbank_dic, cath_dic, schisto_cath_dic,
                    pfam_dic, schisto_pfam_dic):

  # autovivification nested dictionary
  drugbank_repo_map = AutoVivification()

  #below copied from chembl_repo_map

  # loop over each drug in the dictionary
  for drug in drugbank_dic:

    # dictionary for each drug
    each_drug_dic = {}

    # sanity check the uniprot list is not empty (it should not be empty)
    if drugbank_dic[drug]:
      # loop on list of uniprot
      for target in drugbank_dic[drug]:

        # make list in which to store the cath/pfam
        cath_pfam = []

        # append cath value, only if it exists in the dictionary
        if target in cath_dic:
          cath_pfam.extend(cath_dic[target])

        # append pfam value, only if it exists in the dictionary
        if target in pfam_dic:
          cath_pfam.extend(pfam_dic[target])

        #logger.debug(cath_pfam)
        # check the list is not empy
        if cath_pfam:
        # make dictionary
          each_drug_dic[target] = cath_pfam

      # finished loops for all targets, we have the dictionary
      # with {uniprot1:[list of arch],uniprot2:[list]}
      #logger.debug(each_drug_dic)

      #loop over each uniprot in new dictionary
      for targ in each_drug_dic:

        # dictionary for each target
        each_target_dic = {}
        # sanity check the arch list is not empty:
        if each_drug_dic[targ]:
          # loop over list of architectures
          for arch in each_drug_dic[targ]:
            # empty list for schisto
            schisto_list = []
            # check it exists in the cath dictionary
            if arch in schisto_cath_dic:
              schisto_list.extend(schisto_cath_dic[arch])

            if arch in schisto_pfam_dic:
              schisto_list.extend(schisto_pfam_dic[arch])

            # check list is not empty
            if schisto_list:
              #logger.debug(schisto_list)
              # add list as values in dictionary
              each_target_dic[arch] = schisto_list

              #logger.debug(each_target_dic)

              drugbank_repo_map[drug][targ][arch] = each_target_dic[arch]

  #logger.debug(drugbank_repo_map)
  return drugbank_repo_map
############################################################################




############################################################################
### FILT_SCHISTO_MAP
############################################################################
# filter the chembl_repo_map for the filtered schisto uniprots we are
# interested in

def filt_schisto_map(chembl_repo_map, schisto_filt):
  # empty dictionary

  # autovivification nested dictionary
  schisto_filt_map = AutoVivification()

  for drug in chembl_repo_map:
    #schisto_filt_map[drug] = {}
    for target in chembl_repo_map[drug]:
      #schisto_filt_map[drug][target] = {}
      for arch in chembl_repo_map[drug][target]:
        #logger.debug(arch

        schisto_list = []

        for schisto in chembl_repo_map[drug][target][arch]:
          if schisto in schisto_filt:
            schisto_list.append(schisto)
            if schisto_list:
              schisto_filt_map[drug][target][arch] = schisto_list

  return schisto_filt_map
############################################################################




############################################################################
### CSV_TO_DIC
############################################################################
# take csv file such as uniprot_pdb, return dictionary with first column
# values as keys and ';'-separated values as list

def csv_to_dic(csv_file):


  # empty dictionary
  csv_dic = {}

  # open and read drug_bank input and count number
  lines = file_to_lines(csv_file)

  # read csv lines with the csv reader - deals with quotation marks etc..
  incsv = csv.reader(lines)
  # skip the first line with the headers
  next(incsv)

  # loop over each line
  for line in incsv:
    # empty list to store the pdb ids
    pdb_list = []
    pdb_strip = line[1].split(';')
    for pdb in pdb_strip:
      pdb_list.append(pdb)
  
   #   logger.debug(line)
    csv_dic[line[0]] = pdb_list

  #logger.debug(len(csv_dic))

  return csv_dic

############################################################################




############################################################################
### CSV_TO_LST
############################################################################
# take csv file and return single list of the last line
# it does not properly skip the comment lines! 
# it works but better ADD WRAPPER TO PROPERLY SKIP THE COMMENT LINE!

def csv_to_lst(csv_file):

  # # open and read file
  # lines = file_to_lines(csv_file)
  # # count comment lines
  # comment_count = 0
  # # loop over each line
  # for line in lines:
  #   logger.debug(line)
  #   # skip comment lines
  #   if CONTAINS_COMMENT.match(line):
  #     comment_count = comment_count + 1
  # logger.debug(comment_count)


  with open(csv_file) as f:

    #,quoting=csv.QUOTE_MINIMAL
    # get rows with csv reader
    # the quotechar is for ignoring the single quotes I have in the list
    # otherwise you end up with double quotes in the list
    rows = csv.reader(f, delimiter=',', quotechar='\'', skipinitialspace=True)
    for row in rows:
      # overwrites until it reaches last row
      csv_list = row
      #logger.debug(row)
    
    # order list and rm duplicates
    csv_list = list(set(csv_list))
    csv_list.sort()

  # logger.debug(csv_list)
  # return the list
  return csv_list

############################################################################




############################################################################
### FILTER_DIC_FROM_LIST
############################################################################
# take dictionary and return filtered dictionary with only entries that are
# in the given list

def filter_dic_from_list(dictionary,filt_list):
  filtered_dic = {}

  for item in dictionary:
    if item in filt_list:
      filtered_dic[item] = dictionary[item]

  return filtered_dic

############################################################################




############################################################################
### LIST_SECOND_LEVEL_DIC
############################################################################
# take dictionary of dictionaries and return unique list of the second level
# also for values of a simple dic

def list_second_level_dic(dictionary):
  second_list = []

  for item in dictionary:
    for sec in dictionary[item]:
      # strip white spaces
      sec.strip()
      second_list.append(sec)

  second_list = list(set(second_list))

  return second_list

############################################################################




############################################################################
### LST_DIC
############################################################################
# read lst file and creat dictionary with first column as key and rest as list
def lst_dic(lst_file):
  lines = file_to_lines(lst_file)
  lst_dictionary = {}
  # iterate over lines
  for i in range(0,len(lines)):
    #logger.debug(line)
    # split tab
    splitline = lines[i].split(":")
    #logger.debug(splitline)
    
    # empty list for the het groups
    het_list = []

    # remove (right strip) carriage return and the final ';'
    het_gr = splitline[1].rstrip('\r\n').rstrip(';')
    #het_gr = het_gr.rstrip(' ')
    #logger.debug(het_gr)
    het_split = het_gr.split(";")
    #logger.debug(het_split)
    for het_group in het_split:
      het_list.append(het_group.strip())
    #logger.debug(het_list)
    # populate dictionary, stripping the carriage return
    lst_dictionary[splitline[0].strip()] = het_list
  
  #logger.debug(lst_dictionary)
  return lst_dictionary
############################################################################




############################################################################
### EXCLUDE_VALUES_FROM_DIC
############################################################################
# take dictionary and return filtered dictionary excluding values that do
# come up in list
# flag exclude - keep values that are not in the list
# flag include - only keep values that are in the list
# flag nomatch - keep values that do not match the expression

def exclude_values_from_dic(dictionary, filt_list, flag):
  filtered_dic = {}

  for item in dictionary:
    pass_list = []
    for value in dictionary[item]:
      # if we want to exclude the ones that are in the list
      if flag == 'exclude':
        if value not in filt_list:
          pass_list.append(value)
      # if we want only the ones that are in the list
      elif flag == 'include':
        if value in filt_list:
          pass_list.append(value)

      elif flag == 'nomatch':
        if not filt_list.match(value):
          pass_list.append(value)
    # check the list is not empty
    if pass_list:
      # popolate filtered dic
      filtered_dic[item] = pass_list

  return filtered_dic

############################################################################




############################################################################
### TXT_TO_DIC FUNCTION
############################################################################
# takes txt (comma-sep, with headers) and creates dictionary of header 1 
# vs header 2
def txt_to_dic(input_file, header1, header2):
  # open chembldrugs.txt for reading
  lines = file_to_lines(input_file)
  # get the headers
  headers = lines[0]
  # logger.debug(headers)

  # empty dic
  dic = {}

  # number of header 1 nad 2
  h1 = header_count(headers, "\t", header1)
  h2 = header_count(headers, "\t", header2)

  # populate dictionary
  for i in range(1,len(lines)):
    dic[lines[i].split("\t")[h1]] =  lines[i].split("\t")[h2].rstrip('\r\n')
  

  return dic

############################################################################




############################################################################
### SMI_TO_DIC FUNCTION
############################################################################
# takes smi (comma-sep, without headers) and creates dictionary of header 1 
# (column number n1) vs header 2 (column number n2)
def smi_to_dic(input_file, n1, n2):
  # open for reading
  lines = file_to_lines(input_file)
  #logger.debug(lines[18482])

  # empty dic
  dic = {}

  # populate dictionary
  for i in range(0,len(lines)):
    # check line is not empty string
    split = lines[i].rstrip('\r\n').split("\t")
    
    # check the number of items is the same as the number of items in the
    # first row of the file
    if len(split) == len(lines[0].split("\t")): 
    #or len(split) == (len(lines[0].split("\t"))-1):

      if split[n1].rstrip('\r\n') != '' and split[n2].rstrip('\r\n') != '':
        #logger.debug(split)
        dic[split[n1]] =  split[n2]

  # lenght total file (nb there are new lines!)      
  # logger.debug(len(lines))
  # # lenght dictionary created
  # logger.debug(len(dic))

  return dic

############################################################################




############################################################################
### DIC_TO_TXT
############################################################################
# take dic and write to file as tab-sep file
def dic_to_txt(dic, file_name):

  #try remove file if it exists already
  if os.path.isfile(file_name) == True:
    os.remove(file_name)


  with open(file_name, 'a') as myfile:

    for item in dic:
      line = str(dic[item])+ "\t" + str(item) + "\r\n"
      # logger.debug(line)
      myfile.write(line)
      #myfile.write('\n')
      # don't forget you will have new line at the end!

############################################################################




############################################################################
### BABEL_SMI_TO_SDF
############################################################################
# call open babel to convert smiles into sdf
# add --gen3d for coordinates + " --gen3d"
# -d to delete hydrogens
def babel_smi_to_sdf(input_file, output_file):
  # check if the output exists already
  if os.path.isfile(output_file) == True:
    logger.info('The converted file ' + str(output_file) + 
                ' exists already. If you wish to run the conversion again,' +
                ' delete it.')

  else:
   subprocess.call("babel" + " -ismi " + str(input_file) +
                  " -osdf " + str(output_file) + " -d --gen2d", shell=True)

  # nb this module returns None! it just writes to output.sdf

############################################################################




############################################################################
### SDF_TO_DIC
############################################################################
# takes sdf file and converts in dictionary with key versus value
# nb key has to be unique (eg drugbank identifier), 
# otherwise will be overwritten
def sdf_to_dic(sdf_file, key, value):
  with open(sdf_file) as f:
    line_count = 0
    # empty dic
    dic_from_sdf = {}

    for line in f:
      line_count = line_count + 1
      if key in line:
        db_id = linecache.getline(sdf_file, (line_count+1))
        # strip newline
        db_id = db_id.rstrip('\n')

      if value in line:
        smi_id = linecache.getline(sdf_file, (line_count+1))
        # strip newline
        smi_id = smi_id.rstrip('\n')
        dic_from_sdf[db_id] = smi_id

  #logger.info(len(dic_from_sdf))

  return dic_from_sdf

############################################################################




############################################################################
###  MERGE_DIC
############################################################################
def merge_dic(dic1,dic2,dic3):

  dic_merge = {}
  # each drug
  for item in dic1:
    #list for pdbs
    list2 = []
    # list for cc
    list3 = []

    # each uniprot
    for value in dic1[item]:
      if value in dic2:
        # append pdb values to list
        list2.extend(dic2[value])
        #logger.info(value)
        #logger.info(dic2[value])

    #logger.info(list2)
    # check list is not empty
    if list2:
      #rm duplicates
      list2 = list(set(list2))
      #for each pdb in this list
      for thing in list2:
        # check the pdb is in the dic3
        if thing in dic3:
          # append to list 3
          list3.extend(dic3[thing])


    # before moving to next drug, populate dic
    if list3:
      # rm duplicates
      list3 = list(set(list3))
      item = item.strip(' ')
      dic_merge[item] = list3
  #logger.info(len(dic_merge))

  return dic_merge
############################################################################




############################################################################
### RUN_SMSD
############################################################################
# call SMSD
def run_smsd(query, target, flag, threshold, dic_map=None):
  # flag = 'pair' for pairwise comparison, query and target are dictionaries
  # ids: smiles
  # flag = 'batch' for batch comparison, query is dictionary,
  # target is sdf file


    # run SMSD
  # can also include cwd=SMSD_PATH together with shell=True in the command
  # for instance:
  # sh ./SMSD.sh -Q SMI -q \"CCCCC\" -T SMI -t \"CCCN\" -O SMI -o test.smi
  # -r remove hydrogens
  # -m produce mapping output (molDescriptors.out, mcs.out and .mol files)
  # -b match bond type (bond sensitive, faster run!)
  # -z match rings (this is needed otherwise very slow)
  # -x match atom type... (?)
  # -g for png image
  # recommended options are -r -z -b

  # increase Java max heap size
  # subprocess.Popen(["export JVM_ARGS=\"-Xms1024m -Xmx1024m\""], shell=True)
  # subprocess.Popen(["java -Xmx1024m ..."], shell=True)

  # current directory
  initial_dir = os.getcwd()
  #logger.debug(initial_dir)

  if flag == 'pair_2dic':
    # navigate to SMSD dir
    os.chdir(SMSD_PATH)

    output = open('smsd_run_pair_2dic.txt', 'w')

    # dictionary drugs: list of cc that match
    drug_cc_dic = {}

    drug1 = {}
    drug09 = {}
    drug08 = {}
    drug07 = {}

    #loop over drug in the map
    for drug in dic_map:
      #logger.info(drug)
      # list of cc that match each drug
      match_cc_list = []
      sim1 = []
      sim09 = []
      sim08 = []
      sim07 = []
     
      # check drug is in dic
      if drug in query:
        # get the drug smiles
        drug_smi = query[drug]

        
        # each cc we have in the list
        for cc in dic_map[drug]:
          #logger.info(cc)
          # check if cc is in the dic
          if cc in target:
            # get the smiles
            cc_smi = target[cc]

            # handles errors..
            try:
              subprocess.call("sh SMSD.sh -Q SMI -q \"" + str(drug_smi) + \
                            "\" -T SMI -t \"" + str(cc_smi) + 
                            "\" -r -m -z -b", shell=True)
              # get list from lines in molDescriptors output
              mol_des = file_to_lines("molDescriptors.out")
              #logger.info(mol_des)
        

              # make string out of list
              mol_str = ''.join(mol_des)
              # logger.info(mol_str)
              # sanity check string not empty
              if mol_str != '':

                # tanimoto similarity string or other string
                str_match = 'Tanimoto (Sim.)= '
                # find the string
                str_numb = mol_str.find(str_match)
                sim_index = (str_numb + len(str_match))

                sim_string = mol_str[sim_index:(sim_index+3)]
                # get similarity number and convert to float
                similarity = float(sim_string)

                if similarity >= float(threshold):
                  # append to list
                  match_cc_list.append(cc)

                if similarity >= 1.0:
                  sim1.append(cc)

                if similarity >= 0.9:
                  sim09.append(cc)

                if similarity >= 0.8:
                  sim08.append(cc)

                if similarity >= 0.7:
                  sim07.append(cc)
            except:
              logger.warning('We have skipped one comparison!')
              pass


      # check the list is not empty
      if match_cc_list:
        # add list to dictionary
        drug_cc_dic[drug] = match_cc_list
        #logger.info(drug_cc_dic)

      if sim1:
        drug1[drug] = sim1
      if sim09:
        drug09[drug] = sim09
      if sim08:
        drug08[drug] = sim08
      if sim07:
        drug07[drug] = sim07  
      
    # write to output
    output.write("# similarity 1.0\n")
    output.write(str(drug1)+ "\n")
    output.write("# similarity > 0.9\n")
    output.write(str(drug09)+ "\n")
    output.write("# similarity > 0.8\n")
    output.write(str(drug08)+ "\n")
    output.write("# similarity > 0.7\n")
    output.write(str(drug07)+ "\n")
  
  # close the file
  output.close()


  # ###
  # # pairwise comparison on smile strings
  # ###
  # elif flag == 'pair':
  #   # navigate to SMSD dir
  #   os.chdir(SMSD_PATH)
  #   #logger.info('this is pairwise')
  #   # dictionary drugs: list of cc that match
  #   drug_cc_dic = {}

  #   for drug in query:
  #     drug_smi = query[drug]
  #     #logger.info(drug)
  #     # list of cc that match each drug - with similarity above threshold
  #     match_cc_list = []
  #     for cc in target:
  #       cc_smi = target[cc]
  #       # logger.info(cc)

  #       subprocess.call("sh SMSD.sh -Q SMI -q \"" + str(drug_smi) + \
  #                     "\" -T SMI -t \"" + str(cc_smi) + "\" -r -m -z -b", 
  #                     shell=True)

  #       # get list from lines in molDescriptors output
  #       mol_des = file_to_lines("molDescriptors.out")
  #       #logger.info(mol_des)
  #       # make string out of list
  #       mol_str = ''.join(mol_des)
  #       # logger.info(mol_str)
  #       # tanimoto similarity string or other string
  #       str_match = 'Tanimoto (Sim.)= '
  #       # find the string
  #       str_numb = mol_str.find(str_match)
  #       sim_index = (str_numb + len(str_match))
  #       # get similarity number and convert to float
  #       similarity = float(mol_str[sim_index:(sim_index+3)])

  #       if similarity >= float(threshold):
  #         match_cc_list.append(cc)

  #     # check the list is not empty
  #     if match_cc_list:
  #       # add list to dictionary
  #       drug_cc_dic[drug] = match_cc_list
    

  # ###
  # # batch processing on sdf
  # ###
  # elif flag == 'batch':
  #   logger.info('this is batch')
  #   # dictionary drugs: list of cc that match
  #   drug_cc_dic = {}
  #   # check if the target file is in the current directory
  #   if os.path.isfile(target) == False:
  #     logger.info('uh-oh')
  #     logger.error('The file ' + target + ' cannot be found' +
  #                  ' in the current directory!')
  #     # warning
  #     logger.warning('The program is aborted.')
  #     # exit python
  #     sys.exit()
  #     # logger.debug("cp " + target + " " + SMSD_PATH + "/" + target)

  #   else:
  #     logger.info('alright, the file is here')
  #     # copy the file to the SMSD directory
  #     subprocess.call("cp " + target + " " + SMSD_PATH + "/" + target, 
  #      shell=True)

  #     # move to SMSD directory
  #     os.chdir(SMSD_PATH)
  #     directory = os.getcwd()
  #     logger.debug(directory)

  #     for drug in query:
  #       # list of cc that match each drug - with similarity above threshold
  #       match_cc_list = []
  #       drug_smi = query[drug]
  #       logger.info(drug)

  #       subprocess.call("sh SMSD.sh -Q SMI -q \"" + str(drug_smi) + 
  #                     "\" -T SDF -t " + str(target) + " -m -r -z -b", 
  #                     shell=True)

  #       # get the ones above threshold

  #       # add to dic

  #       # check the list is not empty
  #       if match_cc_list:
  #         # add list to dictionary
  #         drug_cc_dic[drug] = match_cc_list


  # move back to working directory!
  os.chdir(initial_dir)
  directory = os.getcwd()
  #logger.debug(directory)
  
  # return the dictionary
  return drug_cc_dic

############################################################################




############################################################################
### MV_FILE
############################################################################
#takes file, makes copy and moves it to current directory
# checks if file is already there and does not move it
def mv_file(origin, filename, new_name):

  # if the file is not there already
  if os.path.isfile(new_name) == False:
    current_dir = os.getcwd()

    os.chdir(origin)
    subprocess.call("cp " + filename + " " + current_dir + "/" + new_name, 
         shell=True)

    os.chdir(current_dir)


############################################################################




############################################################################
### FILTER_TXT
############################################################################

# in the end we need a dictionary of chembl ids vs uniprot ids
def filter_txt(input_file, output_file, header_name, filt_list):
  # open chembldrugs.txt for reading
  lines = file_to_lines(input_file)


  # get the headers
  headers = lines[0]
  # find header name
  col_header = header_count(headers, "\t", header_name)

  out = open(output_file, 'w')
  out.write(headers)
  #out.write('\n')
  for i in range(1,len(lines)):
    rowsplit = lines[i].split("\t")

    # get the chembl drug and target id values for the row
    col = rowsplit[col_header]

    # only proceed if the target id is not an empty field!
    if col  != "":

      # check if the molecule chembl id is one of the drugs we want
      if col in filt_list:
        out.write(lines[i])
        #out.write('\n')

  # close output file
  out.close()

############################################################################




############################################################################
### RUN_MODELLER
############################################################################
# run modeller, produce homology model
# alignment file name, code of template, code of sequence
def run_modeller(alnfile, knowns, sequence):

  # Homology modeling by the automodel class
  from modeller import *              # Load standard Modeller classes
  from modeller.automodel import *    # Load the automodel class


  #initial_dir = os.getcwd()
  #logger.debug(initial_dir)

  # navigate to modeller path 
  #(not necessary, but just to avoid writing files here)
  #os.chdir(MODELLER_PATH)
  

  log.verbose()    # request verbose output
  env = environ()  # create a new MODELLER environment to build this model in

  # directories for input atom files
  env.io.atom_files_directory = ['.', '../atom_files']

  a = automodel(env, alnfile, knowns, sequence)
  
  # (determines how many models to calculate)
  a.starting_model= 1                 # index of the first model
  a.ending_model  = 1                 # index of the last model

  # make the model
  a.make()                          

  #navigate back to initial dir
  #os.chdir(initial_dir)

############################################################################




############################################################################
### RUN_OR_PICKLE
############################################################################
# run module and dump in pickle or retreive pickle without running module
def run_or_pickle(function_return_obj, function_name, arg1 = None,
                  arg2 = None, arg3 = None, arg4 = None, arg5 = None):

  # make string with pickle name
  pickle_name = (function_return_obj + ".p")
  #logger.debug(pickle_name)

  # check if pickle file exists
  if os.path.isfile(pickle_name) == True:
    # retrieve pickle
    function_return_obj = pickle.load(
                          open((str(function_return_obj) +".p"),"rb"))
    logger.debug('We have pickled ' + str(pickle_name))
  # otherwise we want to run the function
  else:
    # case 1: no arguments
    if (arg1 == None and arg2 == None and arg3 == None and arg4 == None and
        arg5 == None):

      function_return_obj = function_name()

    # case 2: one argument
    elif arg2 == None:
      function_return_obj = function_name(arg1)

    # case 3: two arguments
    elif arg3 == None and arg4 == None and arg5 == None:
      function_return_obj = function_name(arg1, arg2)

    # case 4: three arguments
    elif arg4 == None and arg5 == None:
      function_return_obj = function_name(arg1, arg2, arg3)

    # case 5: four arguments
    elif arg5 == None:
      function_return_obj = function_name(arg1, arg2, arg3, arg4)

    #case 6: all arguments
    else:
      function_return_obj = function_name(arg1, arg2, arg3, arg4, arg5)

    # dump result in pickle
    pickle.dump(function_return_obj, open(pickle_name, "wb"))

  # return what the function returned or the pickle
  return function_return_obj

############################################################################




############################################################################
### MAIN FUNCTION
############################################################################

def main():
  # greeting
  logger.info("Hi there, you are running drug_repo.py for repositioning " +
              "of known drugs for schistosomiasis." +
              " Let's do some mapping!")
  

  #################################
  ### PART 1: FIND DRUG TARGETS ###
  #################################
  
  logger.info('PART 1 - We wish to take the ChEMBL input file, ' +
              CHEMBL_INPUT + ', and the DrugBank input file, ' +
              DRUGBANK_INPUT +', map the drug ids to their target ids ' +
              'and obtain a list of unique drug targets.')
  
  # generate chembl dictionary
  chembl_dic = run_or_pickle("1_chembl_dic", process_chembl, CHEMBL_INPUT)

  #logger.info(chembl_dic)
  # get list of uniprot ids from chembl_dic
  chembl_uniprot_list = run_or_pickle("1_chembl_uniprot_list",
                                      flatten_dic, chembl_dic, "values")

  logger.info(str(len(chembl_dic)) + ' ChEMBL drugs could be mapped to ' +
               str(len(chembl_uniprot_list)) + ' unique UniProt ID.')


  # generate drugbank_dictionary
  drugbank_dic = run_or_pickle("1_drugbank_dic", process_drugbank, 
                              DRUGBANK_INPUT)

  #logger.info(len(drugbank_dic))

  # get list of uniprot ids from drugbank
  drugbank_uniprot_list = run_or_pickle("1_drugbank_uniprot_list",
                                    flatten_dic, drugbank_dic, "values")
  

  logger.info(str(len(drugbank_dic)) + ' DrugBank drugs could be mapped to ' +
               str(len(drugbank_uniprot_list)) + ' unique UniProt ID.')


  # merge lists and rm duplicates
  uniprot_list = run_or_pickle("1_uniprot_list", merge_lists,
                              chembl_uniprot_list, drugbank_uniprot_list)

  ### OVERWRITE UNIPROT_LIST WITH MADE-UP LIST
  # overwrite the list with a small set ['B6DTB2', 'Q4JEY0','P11511']
  #['Q4JEY0', 'P68363', 'P10613', 'P18825', 'Q9UM73', 'E1FVX6']
  #uniprot_list = ['Q4JEY0', 'P68363', 'P10613','P18825']
  ###

  logger.info('We have obtained a unique list of ' + str(len(uniprot_list)) +
              ' drug targets.')

  logger.info('------------------- END OF PART 1 -------------------')


  ############################
  ### PART 2: FIND ARCH    ###
  ############################

  logger.info('PART 2 - We wish to build dictionaries of ' +
              'the targets\' Uniprot ids to CATH/Uniprot ids.')

  # run or pickle uniprot_to_arch to retrieve cath domain architectures
  cath_dic = run_or_pickle("2_cath_dic", uniprot_to_arch, uniprot_list, 
                          "cath")

  #logger.debug(len(cath_dic))

  # generate list, flatten it and rm duplicates
  cath_list = run_or_pickle("2_cath_list", flatten_dic, cath_dic, "values")

  logger.info('We have mapped ' + str(len(cath_dic)) + ' uniprot ids to ' +
              str(len(cath_list)) + ' CATH ids.')

  # run or pickle uniprot_to_arch to retrieve pfam domain architectures
  pfam_dic = run_or_pickle("2_pfam_dic", uniprot_to_arch, uniprot_list, 
                          "pfam")

  #logger.debug(len(pfam_dic))

  # generate list, flatten it and rm duplicates
  pfam_list = run_or_pickle("2_pfam_list", flatten_dic, pfam_dic, "values")
  
  logger.info('We have mapped ' + str(len(pfam_dic)) + ' uniprot ids to ' +
              str(len(pfam_list)) + ' Pfam ids.')
  
  logger.info('------------------- END OF PART 2 -------------------')


  ####################################
  ### PART 3: FIND SCHISTO TARGETS ###
  ####################################
  
  logger.info('PART 3 - We wish to map the CATH/Pfam ids ' +
              'to UniProt ids of the taxonomic ids ' + str(TAXA) + '.')
  
  # call archindex on cath values to find the ones from schisto
  uniprot_schisto_cath_dic = run_or_pickle("3_uniprot_schisto_cath_dic", 
                                          arch_to_uniprot, cath_list, "cath")
  #logger.debug(len(uniprot_schisto_cath_dic))

  # generate list, flatten it and rm duplicates
  uniprot_schisto_cath_list = run_or_pickle("3_uniprot_schisto_cath_list",
                              flatten_dic, uniprot_schisto_cath_dic, "values")

  logger.info('We have mapped ' + str(len(uniprot_schisto_cath_dic)) + 
              ' CATH ids to ' + str(len(uniprot_schisto_cath_list)) +
              ' Uniprot ids.')

  # call archindex on pfam values to find ones from schisto
  uniprot_schisto_pfam_dic = run_or_pickle("3_uniprot_schisto_pfam_dic", 
                                          arch_to_uniprot, pfam_list, "pfam")
  #logger.debug(len(uniprot_schisto_pfam_dic))

  # generate list, flatten it and rm duplicates
  uniprot_schisto_pfam_list = run_or_pickle("3_uniprot_schisto_pfam_list",
                              flatten_dic, uniprot_schisto_pfam_dic, "values")

  logger.info('We have mapped ' + str(len(uniprot_schisto_pfam_dic)) + 
              ' CATH ids to ' + str(len(uniprot_schisto_pfam_list)) +
              ' Uniprot ids.')

  # merge and rm duplicates
  # this is total list of unique schisto uniprot ids
  uniprot_schisto_list = run_or_pickle("3_uniprot_schisto_list", merge_lists,
                        uniprot_schisto_cath_list, uniprot_schisto_pfam_list)
  
  logger.info('In total, we have identified ' + 
              str(len(uniprot_schisto_list)) + 
              ' unique targets that point to known drugs.')

  ### OVERWRITE UNIPROT_SCHISTO_LIST WITH MADE-UP LIST
  # this one is the 10 reviewd results ['P13566','Q9U8F1','P33676',
  #'P30114','Q26499','P16641','C4PZQ3','P37227','C4QCD2','Q5D8V5']
  #example of unreviewed entries: 'C7TY75', 'G4LXF4', 'C1L491'
  #uniprot_schisto_list = ['P13566','Q9U8F1','P33676',
  #'P30114','Q26499','P16641','C4PZQ3','P37227','C4QCD2','Q5D8V5']
  ###

  # filter list for only reviewed ones
  uniprot_schisto_filt = run_or_pickle("3_uniprot_schisto_filt",
                                        expasy_filter,
                                        uniprot_schisto_list, "reviewed")

  ### OVERWRITE FILTERED LIST
  #uniprot_schisto_filt = ['P33676']
  ###

  logger.info('Of those targets, the reviewed Uniprot entries are ' + 
              str(len(uniprot_schisto_filt)) +  '.')
  
  logger.info('------------------- END OF PART 3 -------------------')


  ############################
  ### PART 4 GENERATE MAPS ###
  ############################
  logger.info('PART 4 - We wish to create two dictionaries that collect ' +
              'all the mapping so far, one for ChEMBL and one for DrugBank.')

  # generate big map for chembl drugs
  chembl_repo_map = run_or_pickle("4_chembl_repo_map", chembl_repo, 
                                  chembl_dic, cath_dic,
                                  uniprot_schisto_cath_dic, pfam_dic, 
                                  uniprot_schisto_pfam_dic)
  # logger.debug(len(chembl_repo_map))
  logger.info('We have built the ChEMBL map, mapping ' +
              str(len(chembl_repo_map)) + ' ChEMBL drugs to potential ' +
              str(TAXA) + ' targets.')

  # list of drugs that are in the map, to be used in part 6
  #chembl_repo_drug_list = chembl_repo_map.keys()
  chembl_repo_drug_list = flatten_dic(chembl_repo_map, 'keys')
  #logger.info(chembl_repo_drug_list)

  # generate big map for drugbank drugs
  drugbank_repo_map = run_or_pickle("4_drugbank_repo_map", drugbank_repo, 
                                    drugbank_dic, cath_dic,
                                    uniprot_schisto_cath_dic, pfam_dic, 
                                    uniprot_schisto_pfam_dic)
  
  logger.info('We have built the DrugBank map, mapping ' +
              str(len(drugbank_repo_map)) + ' DrugBank drugs to potential ' +
              str(TAXA) + ' targets.')

  # list of drugs that are in the map, to be used in part 6
  # below old one, had white spaces!
  #drugbank_repo_drug_list = drugbank_repo_map.keys()
  #logger.debug(drugbank_repo_drug_list)
  # new list, no white spaces!
  drugbank_repo_drug_list = flatten_dic(drugbank_repo_map, 'keys')
  logger.debug(drugbank_repo_drug_list)

  # filtered ap for reviewed entries!
  # this one should then include the drugbank entries once they are ready
  # obtain filtered mapping dictionary for filtered entries
  chembl_schisto_filt_map = run_or_pickle("4_chembl_schisto_filt_map",
                                          filt_schisto_map, chembl_repo_map,
                                          uniprot_schisto_filt)


  drugbank_schisto_filt_map = run_or_pickle("4_drugbank_schisto_filt_map",
                                            filt_schisto_map, 
                                            drugbank_repo_map,
                                            uniprot_schisto_filt)


  #logger.debug(chembl_schisto_filt_map)
  #logger.debug(drugbank_schisto_filt_map)
  logger.info('------------------- END OF PART 4 -------------------')


  #################################################
  ### PART 5 PDB TO HET GROUPS                  ###
  #################################################
  logger.info('PART 5 - We wish to map all available pdb structures ' +
              'to the Het groups the contain, and then filter out ' +
              'the Het groups contained in ' + POINTLESS_HET + 
              ', a list of ions, metals, peptidic ligands, etc.')
  # make dictionary of pdb to ligands
  pdb_lig_dic = run_or_pickle("5_pdb_lig_dic", lst_dic, PDB_LIG)

  logger.info('We made a dictionary of '+ str(len(pdb_lig_dic)) + 
            ' pdb entries mapped to their ligand identifiers.')

  # make list of ccs to ignore
  pointless_het = run_or_pickle("5_pointless_het", csv_to_lst,
                                    POINTLESS_HET)
  logger.info("The list of ligands we wish to ignore " +
              "contains " + str(len(pointless_het)) + " ligands.")


  # filter dictionary pdb to lig, excluding lig that are in the 'pointless'
  # list
  pdb_lig_pointless_dic = run_or_pickle("5_pdb_lig_pointless_dic",
                                    exclude_values_from_dic, pdb_lig_dic, 
                                    pointless_het, "exclude")
  #logger.debug(len(pdb_lig_pointless_dic))
  
  # second filter, to eliminate those with dash
  # this is filtered dic of all useful pdbs (with useful ligands!)
  pdb_lig_filt_dic = run_or_pickle("5_pdb_lig_filt_dic",
                                    exclude_values_from_dic, 
                                    pdb_lig_pointless_dic, 
                                    CONTAINS_DASH, "nomatch")
  #logger.info(pdb_lig_filt_dic)
  
  # list of 'acceptable' pdbs (with useful ligands) from dic
  pdb_w_lig_list = run_or_pickle("5_pdb_w_lig_list", flatten_dic, 
                                pdb_lig_filt_dic, "keys")
  # the length here is obviously the same as the length of dic!
  #logger.info(pdb_w_lig_list)

  # list of 'acceptable' ligands from dic
  filtered_ligs = run_or_pickle("5_filtered_ligs", flatten_dic,
                                pdb_lig_filt_dic, "values")
  #logger.debug(filtered_ligs)


  logger.info('We have excluded the pdb entries that only have ' +
              'ligands from such list, ' + 
              'to obtain ' + str(len(pdb_lig_filt_dic)) +
              ' pdb entries, mapped to a total of ' +
              str(len(filtered_ligs)) + ' unique ligands.')

  logger.info('------------------- END OF PART 5 -------------------')


  ##################################################
  ### PART 6 DRUG TARGETS WITH STRUCTURAL INFO   ###
  ##################################################

  logger.info('PART 6 - We wish to collect all the drug targets that ' +
              'point to some repositioning target, point them to ' +
              'the available pdb structures (using ' + UNIPROT_PDB + 
                '), filter them according to the map obtained in Part 4 ' +
                'and extract the ligands (using ' + CC_SMI + ').')
  # obtain list of targets from drugbank_repo_map and chembl_repo_map
  # these are all the uniprot values that are targets of our potential
  # drug repo candidates
  chembl_drug_targ = run_or_pickle("6_chembl_drug_targ", 
                                  list_second_level_dic, chembl_repo_map)
  #logger.info(chembl_drug_targ)
  
  drugbank_drug_targ = run_or_pickle("6_drugbank_drug_targ", 
                                  list_second_level_dic, drugbank_repo_map)

  # logger.debug(len(drugbank_drug_targ))

  tot_drug_targ = run_or_pickle("6_tot_drug_targ", merge_lists, 
                                chembl_drug_targ, drugbank_drug_targ)

  logger.info('Overall, we have ' + str(len(tot_drug_targ)) + 
              ' drug targets that could be mapped to some schisto target.')

  # make dictionary uniprot to pdb
  uniprot_pdb_dic = run_or_pickle("6_uniprot_pdb_dic", csv_to_dic, 
                                  UNIPROT_PDB)
  #logger.debug(uniprot_pdb_dic)

  # this is dictionary of drug targets that have at least one pdb structure
  uniprot_filt = run_or_pickle("6_uniprot_filt", filter_dic_from_list, 
                              uniprot_pdb_dic, tot_drug_targ)

  #logger.info(uniprot_filt)

  logger.info('Of those targets, ' + str(len(uniprot_filt)) + 
              ' have at least one pdb structure associated to them.')
  # apply filter
  #logger.debug(uniprot_filt)
 
  #####
  # this would be alternative method for finding entries with pdb
  # BUT! it returns larger list (eg 2751 instead of 2711) because it includes
  # pdb ids that point to model structures, not accepted in the pdb anymore
  # # obtain filtered list of drug targets that have associated pdbs
  # uniprot_filt_pdb = run_or_pickle("5_uniprot_filt_pdb", expasy_filter, 
  #                                 uniprot_list, "pdb")
  #####


  # take dic of drug target uniprot to pdb and keep only ones that 
  # are in in the 'acceptable' pdb list
  uniprot_pdb_w_lig = run_or_pickle("6_uniprot_pdb_w_lig", 
                                    exclude_values_from_dic, uniprot_filt,
                                    pdb_w_lig_list, "include")
  #logger.info(uniprot_pdb_w_lig)

  ###
  # get list of uniprot from dic above
  uniprot_w_lig_list = uniprot_pdb_w_lig.keys()
  logger.info(len(uniprot_w_lig_list))

  ###

  # get the pdb list from the dic above
  pdb_w_lig = run_or_pickle("6_pdb_w_lig", list_second_level_dic,
                                uniprot_pdb_w_lig)
  
  logger.info('Of those, ' + str(len(uniprot_pdb_w_lig)) +
              ' have at least one pdb structure ' +
              'in complex with a small molecule associated to them. ' +
              'The unique pdb structures are ' + str(len(pdb_w_lig)) + '.')


  # now filter the pdb_lig_filt_dic, to obtain the pdbs we want
  # { PDBID: [list of CC]}
  # this will be the dic we refer to later!
  pdb_cc_dic = run_or_pickle("6_pdb_cc_dic", filter_dic_from_list, 
                                pdb_lig_filt_dic, pdb_w_lig)


  # finally obtain the list of cc we need! - the ones that are in the pdbs
  # this is the list of cc we need to try and match to the drugs cc!!
  # will be around 8435 in the list
  cc_list = run_or_pickle("6_cc_list", list_second_level_dic,
                          pdb_cc_dic)
  logger.info('We have extracted the chemical components from the pdbs, ' +
              'for a total of ' + str(len(cc_list)) + ' chemical components')

  # get cc to smiles dictionary
  cc_smiles = run_or_pickle("6_cc_smiles", smi_to_dic, CC_SMI, 1, 0)

  #logger.info(len(cc_smiles))


  # dic of cc we ar interested in, mapped to their smiles
  cc_smi_filt = run_or_pickle("6_cc_smi_filt", filter_dic_from_list, 
                              cc_smiles, cc_list)
  
  logger.info('We have mapped ' + str(len(cc_smi_filt)) + 
              ' of these chemical components to their smiles.')
  
  logger.info('------------------- END OF PART 6 -------------------')


  ####################################
  ### PART 7 CHEMBL CLUSTERING   ###
  ####################################
  logger.info('PART 7 - We wish to take the ChEMBL drugs ' +
              'from the mapping and cluster them against ' +
              'the chemical components extracted from the pdb structures.')

  # total chembl drugs to smiles dictionary - 10406 chembl drugs
  chembl_id_smi_dic = run_or_pickle("7_chembl_id_smi_dic", txt_to_dic, 
                                    CHEMBL_INPUT, "CHEMBL_ID",
                                    "CANONICAL_SMILES")
  #logger.debug(len(chembl_id_smi_dic))
  

  # filter dictionary to only drugs that are in chembl_repo_drug_list
  # these are all chembl drugs (783) that are in the map
  chembl_id_smi_filt = run_or_pickle("7_chembl_id_smi_filt", 
                                      filter_dic_from_list, 
                                      chembl_id_smi_dic,chembl_repo_drug_list)
  
  logger.info('We have mapped the ' + str(len(chembl_id_smi_filt)) +
              ' ChEMBL drugs to their smiles.')


  # filter chembl_dic to only the 783 drugs, using chembl_repo_drug_list
  chembl_dic_mapped_drugs = filter_dic_from_list(chembl_dic, 
                            chembl_repo_drug_list)
  #logger.info(len(chembl_dic_mapped_drugs))
  # filter out the uniprots, using uniprot_w_lig_list
  chembl_dic_uni_drugs = exclude_values_from_dic(chembl_dic_mapped_drugs, 
                        uniprot_w_lig_list, "include")
  #logger.info(len(chembl_dic_uni_drugs))
  chembl_uni_drugs_list = chembl_dic_uni_drugs.keys()
  #logger.info(len(chembl_uni_drugs_list))
  # filter chembl_id_smi_filt to what obtained above
  chembl_id_smi_opt = filter_dic_from_list(chembl_id_smi_filt, 
                      chembl_uni_drugs_list) 
  #logger.info(len(chembl_id_smi_opt))
  

  # obtain drug to cc dictionary, merging three dics
  # this is all the drugs in the map, pointing to the cc in the pdbs of
  # of their targets
  chembl_to_cc = merge_dic(chembl_dic,uniprot_filt, pdb_cc_dic)
  #logger.info(len(chembl_to_cc))


  logger.info('We have filtered out the ChEMBL drugs that ' +
              'do not point to a crystal structure in complex with ' +
              'a small molecule, to obtain ' + str(len(chembl_id_smi_opt)) +
              ' ChEMBL drugs mapped to their smiles' +
              '; these will be clustered.')


  #####################
  #openbabel conversion - not necessary for now
  #####################
  # # cc: create file with smiles to feed to openbabel
  # dic_to_txt(cc_smi_filt, '6_cc_smi_filt.smi')

  # # ligands converted to sdf
  # # babel_smi_to_sdf('test.smi','test.sdf')

  # # ligands converted to sdf 3d and no hydrogens
  # #babel_smi_to_sdf('test.smi','test_noh.sdf')

  # # convert smiles to sdf
  # babel_smi_to_sdf('6_cc_smi_filt.smi','6_cc_smi_filt.sdf')
  
  # # this number is the same number of entries I should obtained in the 
  # # SMSD output!! check!
  # logger.info('We have mapped ' + str(len(cc_smi_filt)) + 
  #             ' small-molecule chemical components to their smiles, ' +
  #             'and converted them to 3d sdf.')

  # or do conversion in separate shell
  # same command (with gen3d and hydrogen removed)
  #babel_smi_to_sdf('cc_smi_filt.smi','cc_smi_filt.sdf')
  # logger.info(chembl_id_smi_filt)
  #######################


  # possibly test with catcvs input as well before proceeding


  # convert dic into smile file (module return none, it just writes to file)
  #dic_to_txt(cc_smi_filt, 'cc_smi_filt.smi')
  

  # # OVERWRITE CHEMBL
  # chembl_id_smi_filt = {'CHEMBL1115': 'CN(C)C(=O)Oc1ccc[n+](C)c1', 
  #'CHEMBL965': 'C[N+](C)(C)CCOC(=O)N', 
  #'CHEMBL964': 'CCN(CC)C(=S)SSC(=S)N(CC)CC'}
  #logger.info(chembl_id_smi_filt)

  # # cc: create file with smiles to feed to openbabel
  #dic_to_txt(cc_smi_filt, 'test.smi')

  # # ligands converted to sdf
  #babel_smi_to_sdf('test.smi','test.sdf')


  # TEST
  # logger.info('Start test')
  # now = datetime.now()
  # test = run_or_pickle("test", run_smsd, chembl_id_smi_opt,
  #                      cc_smi_filt,"pair_2dic", 1.0, chembl_to_cc)
  # then = datetime.now()
  # logger.info(test)
  # tdelta = then - now
  # logger.info('End test')
  # logger.info(tdelta)


  # # CHEMBL CLUSTERING (takes an hour approx)
  # rn clustering with Tanimoto similarity threshold
  # thresholds for similarity at 1, 0.9, 0.8, 0.7 are also written to output:

  chembl_cluster = run_or_pickle("7_chembl_cluster", run_smsd, 
                                chembl_id_smi_opt, cc_smi_filt,
                                "pair_2dic", SIM_THRESHOLD, chembl_to_cc)
  logger.info(chembl_cluster)
  # move output file to current dir
  mv_file(SMSD_PATH, 'smsd_run_pair_2dic.txt', '7_chembl_cluster.txt')

  logger.info('We have clustered the ChEMBL drugs, to obtain ' + 
              str(len(chembl_cluster)) + ' drugs mapped to at least ' +
              'a chemical component with Tanimoto similarity above ' +
              str(SIM_THRESHOLD) + 
              ' (other similarity thresholds written to file).')


  # get the list of drugs from cluster dic
  chembl_cluster_list = flatten_dic(chembl_cluster, "keys")
  logger.info(len(chembl_cluster_list))

  # find how it relates to the maps
  # chembl_repo_map - big map
  # chembl_schisto_filt_map - only ones with annotated schisto targ
  logger.info(chembl_schisto_filt_map)
  this = filter_dic_from_list(chembl_schisto_filt_map,chembl_cluster_list)
  logger.info(this)
  
  # write filtered txt csv file to be imported in excel
  filter_txt('chembl_drugs.txt', '7_chembl_clust_excel.txt', 'CHEMBL_ID', 
             chembl_cluster_list)

  logger.info(chembl_repo_map['CHEMBL973'])


  # # tanimoto 0.9
  # chembl_cc_09 = run_or_pickle("7_chembl_cc_09", run_smsd,
  #                               chembl_id_smi_opt,cc_smi_filt,"pair", 0.9)
  # # tanimoto 1.0
  # chembl_cc_1 = run_or_pickle("7_chembl_cc_1", run_smsd,
  #                               chembl_id_smi_opt,cc_smi_filt,"pair", 1.0)
  # #logger.info(chembl_cc_02)


  logger.info('------------------- END OF PART 7 -------------------')

  ####################################
  ### PART 8 DRUGBANK CLUSTERING   ###
  ####################################
  logger.info('PART 8 - In the same way, we wish to take ' +
            'the DrugBank drugs from the mapping and cluster them against ' +
              'the chemical components extracted from the pdb structures.')

  # drugbank drugs to smiles dictionary (total 6799 drugs mapped to smiles)
  drugbank_id_smi_dic = run_or_pickle('8_drugbank_id_smi_dic', 
                                      sdf_to_dic, DRUGBANK_SDF, 
                                      'DATABASE_ID', 'SMILES')
  # logger.info(drugbank_id_smi_dic)
  

  # filter dictionary to only drugs that in the drugbank_repo_drug_list
  drugbank_id_smi_filt = run_or_pickle("8_drugbank_id_smi_filt", 
                                      filter_dic_from_list, 
                                      drugbank_id_smi_dic,
                                      drugbank_repo_drug_list)
  
  #logger.info(len(drugbank_id_smi_filt))
  #logger.info(drugbank_repo_drug_list)

 
  logger.info('We have mapped ' + str(len(drugbank_id_smi_filt)) +
              ' DrugBank drugs to their smiles.')

  # obtain drug to cc dictionary, merging three dics
  drugbank_to_cc = merge_dic(drugbank_dic,uniprot_filt, pdb_cc_dic)
  #logger.info(len(drugbank_to_cc))
  
  logger.info('We have filtered the drugs, as before, to obtain ' + 
              str(len(drugbank_to_cc)) +
              ' DrugBank drugs that will be clustered.')


  # splitting drugbank_to_cc into 5 chunks
  items1,items2,items3, items4, items5 = \
                        zip(*izip_longest(*[iter(drugbank_to_cc.items())]*5))
  d1 = dict(item for item in items1 if item is not None)
  d2 = dict(item for item in items2 if item is not None)
  d3 = dict(item for item in items3 if item is not None)
  d4 = dict(item for item in items4 if item is not None)
  d5 = dict(item for item in items5 if item is not None)
  
  logger.info('We have split the drugbank entries into chunks of ' +
              str(len(d1)) + ', ' + str(len(d2)) + ', ' +
              str(len(d3)) + ', ' + str(len(d4)) + ' and ' + 
              str(len(d5)) + ', for easier processing.')


  # 1st
  logger.info('We are processing the first chunk.')
  db1_cluster = run_or_pickle("8_db1_cluster", run_smsd, 
                                drugbank_id_smi_filt, cc_smi_filt,
                                "pair_2dic", SIM_THRESHOLD, d1)
  
  mv_file(SMSD_PATH, 'smsd_run_pair_2dic.txt', '8_db1_cluster.txt')
  #logger.info(len(drugbank_cluster))
  #2nd
  logger.info('We are processing the second chunk.')
  db2_cluster = run_or_pickle("8_db2_cluster", run_smsd, 
                                drugbank_id_smi_filt, cc_smi_filt,
                                "pair_2dic", SIM_THRESHOLD, d2)
  
  mv_file(SMSD_PATH, 'smsd_run_pair_2dic.txt', '8_db2_cluster.txt')

  #3rd
  logger.info('We are processing the third chunk.')
  db3_cluster = run_or_pickle("8_db3_cluster", run_smsd, 
                                drugbank_id_smi_filt, cc_smi_filt,
                                "pair_2dic", SIM_THRESHOLD, d3)
  
  mv_file(SMSD_PATH, 'smsd_run_pair_2dic.txt', '8_db3_cluster.txt')

  #4th
  logger.info('We are processing the fourth chunk.')
  db4_cluster = run_or_pickle("8_db4_cluster", run_smsd, 
                                drugbank_id_smi_filt, cc_smi_filt,
                                "pair_2dic", SIM_THRESHOLD, d4)
  
  mv_file(SMSD_PATH, 'smsd_run_pair_2dic.txt', '8_db4_cluster.txt')

  #5th
  logger.info('We are processing the fifth chunk.')
  db5_cluster = run_or_pickle("8_db5_cluster", run_smsd, 
                                drugbank_id_smi_filt, cc_smi_filt,
                                "pair_2dic", SIM_THRESHOLD, d5)
  
  mv_file(SMSD_PATH, 'smsd_run_pair_2dic.txt', '8_db5_cluster.txt')

  # sum of all the 5 dics!
  tot_db = dict(db1_cluster.items() + db2_cluster.items() + 
                db3_cluster.items() + db4_cluster.items() + 
                db5_cluster.items())

  # tot_db_length = (len(db1_cluster) + len(db2_cluster) + len(db3_cluster) +
  #                 len(db4_cluster) + len(db5_cluster))

  logger.info('We have clustered the DrugBank drugs, to obtain ' + 
              str(len(tot_db)) + ' drugs mapped to at least ' +
              'a chemical component with Tanimoto similarity above ' +
              str(SIM_THRESHOLD) + 
              ' (other similarity thresholds written to file).')

  logger.info(cath_dic["Q02127"])
  logger.info(pfam_dic["Q02127"])
  logger.info('------------------- END OF PART 8 -------------------')


  ####################################
  ### PART 9 HOMOLOGY MODELLING   ###
  ####################################
  logger.info('PART 9 - Homology modelling.')

  # run modeller
  # requires alignment file and pdb file in the working dir
  run_modeller('1d3h_schma.ali', '1d3h','schma')

  
  logger.info('------------------- END OF PART 9 -------------------')


  logger.info('------------------- END OF SCRIPT -------------------')

############################################################################




############################################################################
### call main function, prevent execution on import
############################################################################
if __name__ == "__main__":
  main()
############################################################################