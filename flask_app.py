# packages to import

from flask import Flask, jsonify, request, render_template, redirect, url_for, session
import glob
import os
import random
import os, codecs
import numpy as np
import time
import hashlib
from flask_wtf import form
from wtforms import SubmitField
from flask.ext.sqlalchemy import SQLAlchemy
import sys
from sqlalchemy.orm.session import sessionmaker, make_transient
import time
import math
import json

# set up global counters

from multiprocessing import Value

counter = Value('i', 0)
endcounter = Value('i', 0)
terminate = Value('i', 0)

app = Flask(__name__)
app.config["DEBUG"] = True

# set up database

SQLALCHEMY_DATABASE_URI = "mysql+mysqlconnector://{username}:{password}@{hostname}/{databasename}".format(
    username="awinnicki15",
    password="Aaloha23",
    hostname="awinnicki15.mysql.pythonanywhere-services.com",
    databasename="awinnicki15$comments15",
)
app.config["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DATABASE_URI
app.config["SQLALCHEMY_POOL_RECYCLE"] = 299

db = SQLAlchemy(app)

# set up dictionaries which will store the values affiliated with the sessions

# the amount of time it took each user to complete the survey

time_dict = {}

# the string of radio buttons that were clicked in order

radio_dict = {}

# the session name, or the order that the person started the survey

name_dict = {}

# the comments the person put in , if any

comments_dict = {}

# the current question number the person was on

qs = {}

# the list of the dog images that were shown to the person

v_dict = {}
u_dict = {}

# the string of the dog images that were shown to the person

v = {}
u = {}

# the secret_code that the person put to ensure that they actually finished
# survey

secret_code = {}

# set up database class
# each row in the database stores and id value, radio, name,
# time, list1, list2, and comments value

class Comment(db.Model):

    __tablename__ = "comments"

# id is a counter for number of row in the database table

    id = db.Column(db.Integer, primary_key=True)

# radio is a string which stores the radio button values that the user submitted

    radio = db.Column(db.String(4096))

# name is the session name of the user

    name = db.Column(db.Integer)

# time is the duration it took to finish the survey

    time = db.Column(db.Float)

# list1 is a string which contains the values of the images u which were queried

    u = db.Column(db.String(4096))

# list2 contains the values of the corresponding images v which were queried

    v = db.Column(db.String(4096))

# comments includes the optional comments the user made at the end of the survey

    comments = db.Column(db.String(4096))

# secret code is code that each person who successfully finishes gets

    secret_code = db.Column(db.String(4096))

# when passed, enable the system to recognize placement of the
# items in the database

    def __init__(self, radio, name, time, list1, list2, comments, code):
        self.radio = radio
        self.name = name
        self.time = time
        self.u = list1
        self.v = list2
        self.comments = comments
        self.secret_code = code


# Set up the clusters class which stores the final list of the
# clusters that was obtained when the algorithm is finished

class Clusters(db.Model):

    __tablename__ = "clusters"
    id = db.Column(db.Integer, primary_key=True)

# only row of interest is clusters which stores the list of clusters

    clusters = db.Column(db.String(4096))

    def __init__(self, clusters):
       self.clusters = clusters


# set up constants that are used in the algorithm

nu = 5
delta = .04
no_qs = 5

# V is the list of images that still need to be placed in a cluster

V = list(range(473))


# C is the list of clusters so C[0] is a list which
# contains the elements of the first cluster, C[1]
# is a list which contains the element of the second cluster

i = random.choice(V)
V.remove(i)
C = [[i]]


# listv is the list which determines which vs are currently being on
# queue to be placed in a cluster. Each user will be determining a place
# for the current v.

listv = []

# clusters is a list which contains the cluster number that each v
# is getting checked against. So at a given time, if it is determined
# that a given v in a certain cluster, then the v that was just checked
# is now replaced with another v, the v is placed in a cluster, and iterations
# and averages are reset for that position in the clusters list.
# for example, clusters = [0, 1, 0].
# this means that when a query is to be made with the v[1], you would
# be picking a u out of cluster 2. If it is determined that the v is not
# part of that cluster, you would be incrementing the clusters[1] and then
# ensuring that anyone who clicks submit has the u[session['name']] inside
# the current cluster being queried. same with the v.
# You would ensure that the v[session['name']] is inside the current v
# in the list of v's otherwise you'd disregard it. To check that the
# v is inside the cluster you are looking for, you just need to ensure that
# the C[clusers[qs[session['name']]]] contains u[session['name']].

clusters = []
# iterations is the number of people that finished querying the
# current cluster/v combination that is currently being checked

iterations = []

# averages is the number of Xt of the people that finished querying the
# current cluster/v combination that is currently being checked

averages = []

# Initialize averages, clusters, and iterations.

for i in range(no_qs):
    clusters.append(0)
    averages.append(0)
    iterations.append(1)
    listv.append(random.randint(0, 472))


# psi(t) is the confidence interval as a function of the number of iterations

def psi(t):

    a = math.sqrt((1 + nu) / (2 * t))
    b =  ((1 + math.sqrt(nu)) * a)
    c = math.log((1/delta)*math.log((1+nu)*t))
    return (math.sqrt(c) * b)


# when a user first accesses the webpage, he/she is taken to the index function

@app.route("/", methods=["GET", "POST"])

def index():

# first, it is necessary to determine if the algorithm has been terminated.
# if it has been terminated, you can redirect the user to a page
# that lets the user know that they will not get their money
# and they should just leave the page as the algorithm has been terminated.


# increment the counter value
# which counts the number of people who have tried to access the website

    with counter.get_lock():
        counter.value += 1

# set that the session['name'] which is the key in each dictionary which
# ensures that each user has their own set of variables in the program

    session['name'] = counter.value - 1

# save the current time, which will help determine the duration a user
# spent filling out the survey

    time_dict[session['name']] = time.time()

# save the value in the list of v and u the user is on.
# so when qs[session['name']] = 3, the user is on the 4th question
# so they will access listv[3] and clusters[3] to get the v and then
# a random values in C[clusters[3]] which will give them the current pair
# to query.

    qs[session['name']] = 0

# u_dict is the string which contains the u's that were queried by a given
# user. Each entry is separated by a comma. So for example, the u_dict
# in the database would look like 2, 3, 4

    u_dict[session['name']] = ' '

# u_dict is the string which contains the v's that were queried by a given
# user. Each entry is separated by a comma. So for example, the v_dict
# in the database would look like 2, 3, 4

    v_dict[session['name']] = ' '

# radio_dict is a string which is stored in the database and contains the
# clicks of each user's values that they stored in the database.

    radio_dict[session['name']] = ' '

# once the user loads the page, they can go ahead and move on view the dogs


# initialize the commments

    comments_dict[session['name']] = ' '

# initialize the secret code

    secret_code[session['name']] = "".join([ "0123456789ABCDEF"[random.randint(0,0xF)] for _ in range(32) ])

# if algorithm has finished running, no comments are stored, and just print
# a page that says that survey can't be taken

    if (terminate.value == 1):
        comments_dict[session['name']] = 'none'
        return redirect(url_for('not_available'))

# otherwise, get the u's and v's for the first question that is to be asked

    if (request.method == "GET"):
        v[session['name']] = listv[qs[session['name']]]
        u[session['name']] = random.choice(C[clusters[qs[session['name']]]])
        return redirect(url_for('index2'))
    else:
        return redirect(url_for('index'))

# once the user loads the page, they will be redirected to the set of dogs
# they can compare to aid the clustering algorithm

@app.route("/index2", methods=["GET", "POST"])
def index2():

# if algorithm is done, don't bother saving the results

    if (terminate.value == 1):
        comments_dict[session['name']] = 'none'
        return redirect(url_for('end'))

# ensure that the person accessing the index2 is a user and not just
# someone who skipped the other pages

    elif not 'name' in session:
        return redirect(url_for('index'))
    else:

# ensure that the user is not asked too many questions, if they are about to be
# just redirect them to the end

        if (qs[session['name']] >= no_qs - 1):
            return redirect(url_for('end'))
        else:

            if request.method == 'POST':

# if they finished matching up the dogs, go ahead and store their results
# in the database, and prepare to get the next set of dogs

# first need to ensure that the appropriate user had chosen the button
# otherwise, all users who are working on task would increment their
# questions many of whom weren't the ones who actually submitted the button


                results_dict = dict(request.form)
                if ((request.form["submit"] == 'Submit') and (str(session['name']) in results_dict.keys())):
                        value = results_dict.get(str(session['name']))[0]

# ensure that the user submitted a radio button value, if not, it just shows
# the pictures again, and waits for the user to submit a radio button

                        if ((value == '1') or (value == '0')):

# ensure that the results you are saving are not from a a cluster that
# had finished processing.

                            if ((u[session['name']] in C[clusters[qs[session['name']]]]) and (v[session['name']] == listv[qs[session['name']]])):


# store results in appropriate dictionaries to be later stored in the database

                                radio_dict[session['name']] += value
                                u_dict[session['name']] += str(u[session['name']])+','
                                v_dict[session['name']] += str(v[session['name']])+','

# get old average, the t and new average for the cluster processing algorithm

                                prev_avg = averages[qs[session['name']]]
                                t = iterations[qs[session['name']]]
                                new_avg = float(((t - 1) / t) * prev_avg + (int(value) / t))

# v has found a home in a cluster. Need to place it in cluster, and remove it
# from list of vs to be sorted. If the length of original V has been traversed
# algorithm is finished

                                if (new_avg - psi(t) > .5):
                                    C[clusters[qs[session['name']]]].append(listv[qs[session['name']]])
                                    V.remove(listv[qs[session['name']]])
                                    if (len(V) == 0):
                                        terminate.value = 1
                                        return redirect(url_for('end'))

# otherwise, get a new v, a new set of clusters, and a new average for that v and c
# reset the iterations too

                                    else:
                                        listv[qs[session['name']]] = random.choice(V)
                                        clusters[qs[session['name']]] = 0
                                        averages[qs[session['name']]] = 0
                                        iterations[qs[session['name']]] = 1

# if you need to move on to the next cluster

                                elif (new_avg - psi(t) < .5):

# if you have more clusters to go through, reset the averages and iterations
# but ensure that everyone runs the algorithm on a new set of clusters

                                        if (clusters[qs[session['name']]] < len(C) - 1):
                                            averages[qs[session['name']]] = 0
                                            iterations[qs[session['name']]] = 1
                                            clusters[qs[session['name']]] += 1

# otherwise, you went through the clusters, and you need to make v
# its own cluster, and you need to get a new v, just as you did above

                                        else:
                                            C.append([listv[qs[session['name']]]])
                                            V.remove(listv[qs[session['name']]])
                                            if (len(V) == 0):
                                                terminate.value = 1
                                                return redirect(url_for('end'))
                                            else:
                                                listv[qs[session['name']]] = random.choice(V)
                                                clusters[qs[session['name']]] = 0
                                                averages[qs[session['name']]] = 0
                                                iterations[qs[session['name']]] = 1

# otherwise, keep iterating, updating the avergaes and iterations

                                else:
                                    averages[qs[session['name']]] = new_avg
                                    iterations[qs[session['name']]] += 1

# if you submitted a radio button, but your results are not
# needed, blanks are stored in the radio buttons and u and v dicts

                            else:
                                radio_dict[session['name']] += '-'
                                u_dict[session['name']] += '-,'
                                v_dict[session['name']] += '-,'

# update the question number

                            qs[session['name']] = qs[session['name']] + 1

# determine their next u and v in Query(u, v)

# set their v

                            v[session['name']] = listv[qs[session['name']]]

# set their u

                            u[session['name']] = random.choice(C[clusters[qs[session['name']]]])

                            return redirect(url_for('index2'))

            return render_template("main_page3.html", u=u[session['name']], v=v[session['name']], no=qs[session['name']] + 1, name=session['name'])

# your questions are over

@app.route("/end", methods=["GET", "POST"])
def end():

    if not 'name' in session:
        return redirect(url_for('index'))

# upload their comments if they had them, and even if they didn't
# just redirect them to their secret code page

    else:
        if request.method == 'POST':
            if (request.form["Done"] == 'Submit'):
                comments_dict[session['name']] = request.form["comment"]
                return redirect(url_for('finale'))
        return render_template("end.html")

# the algorithm is finished - so just post that , and save the
# clusters in the clusters database

@app.route("/not_available", methods=["GET", "POST"])
def not_available():
    clusters_final=Clusters(str(C))
    db.session.add(clusters_final)
    db.session.commit()
    return render_template("na.html", secret = secret_code[session['name']])

# and someone has submitted results, so you need to save their results
# and then show them their secret code

@app.route("/finale", methods=["GET", "POST"])
def finale():

        #clusters_final=Clusters(str(C))
        #db.session.add(clusters_final)
        #db.session.commit()

# save their time

        final_time = time.time()
        time_diff = final_time - time_dict[session['name']]

# save their us except the last comma, same for v

        c = u_dict[session['name']][:-1]
        d = v_dict[session['name']][:-1]

# store the user's results in database

        radio_show=Comment(radio_dict[session['name']], session['name'], time_diff, c, d, comments_dict[session['name']], secret_code[session['name']])
        db.session.add(radio_show)
        db.session.commit()
        endcounter.value += 1
        return render_template("Done.html", secret = secret_code[session['name']])
        print(C)

app.secret_key = 'i love candy and pugs'
