# -*- coding: utf-8 -*-
"""
Created on Wed Jun 27 13:30:48 2018

@author: pedrobw
"""

import time
import Project
import ASTgen
import gumtreeASTparser
import Print

def test_ASTparsing():
    path = "/media/pedrobw/6A384D7F384D4AF1/Users/Administrator/Examples/" + \
           "Backporting/Buffer_Overflow-Espruino/Pc/"
    project = Project.Project(path, "P")
    path_to_file = "targets/esp8266/esp8266_board_utils.c"
    file = path + path_to_file
    ASTgen.parseAST(file, project)
    
    
def test_gumtreeParsing1():
    for i in gumtreeASTparser.AST_from_file("gumtree_parse_test"):
        Print.white(i)
    
    
def test_gumtreeParsing2():
    l = gumtreeASTparser.AST_from_file("gumtree_parse_test")
    root = l[-1]
    gumtreeASTparser.recursive_print(root)
        

def run():
    Print.title("Running crochet tests...")
    tests = [test_ASTparsing, test_gumtreeParsing1, test_gumtreeParsing2]
    for i in tests:
        Print.green("-"*120)
        Print.rose("Starting test " + str(i.__name__) + "...")
        print("")
        start = time.time()
        i()
        end = time.time()
        secs = str(end - start)
        print("")
        Print.rose("Successful test after " + secs + " seconds.")
        print("")
    Print.green("-"*150)
    

if __name__=="__main__":
    run()