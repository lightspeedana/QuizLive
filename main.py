from flask import Flask, render_template, request, redirect, url_for, session
from flask_mysqldb import MySQL
import MySQLdb.cursors
import re

app = Flask(__name__)

app.secret_key = 'Mgh4tMzjHDmEJM199nDZ'

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'm^3X3!5eUBtg'
app.config['MYSQL_DB'] = 'siteLogin'

mysql = MySQL(app)

