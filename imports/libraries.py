from flask import Flask, render_template, request, jsonify, redirect, session, url_for, flash

# MongoDB-related imports
import pymongo
from pymongo import MongoClient
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from bson import ObjectId, json_util

# Security & Authentication
import bcrypt
from functools import wraps

# Deep Learning & Transformers
import torch
from transformers import pipeline

# Date & Time
from datetime import datetime, timedelta

# File Handling
import os
from werkzeug.utils import secure_filename
