# -*- coding: utf-8 -*-
from imports.libraries import *


# Chatbot Model 
# ---------------------------------------------------------------------------------------- #
application = Flask(__name__)
application.secret_key = 'p26b5LZUEGuPkvekv6ZzkwInufEDyjfT'

model_path = "Chatbot/Models/models--deepset--roberta-base-squad2/snapshots/adc3b06f79f797d1c575d5479d6f5efe54a9e3b4"
question_answer = None

def get_qa_model():
    global question_answer
    if question_answer is None:
        question_answer = pipeline("question-answering", model=model_path, torch_dtype=torch.bfloat16)
    return question_answer


# Database
# ------------------------------------------------------------------------------------------- #
client = MongoClient('mongodb://localhost:27017/')
db = client.mydatabase
collection_donor_details = db.donarData
collection_patient_details = db.patientData
collection_users_query = db.queryData
collection_users_details = db.users
collection_chatbot_feedback = db.chatbot_feedback
collection_testimonials = db.testimonials
collection_patient_reviews = db.patient_reviews
collection_timeline = db.patient_timeline
collection_notifications = db.notifications
collection_matches = db.matches
collection_doctors = db.doctors


# Admin Required
# ------------------------------------------------------------------------------------- #
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_admin_logged_in():
            flash('Access denied. Administrative login required.', 'error')
            return redirect(url_for('admin'))
        return f(*args, **kwargs)
    return decorated_function



# Home Page 
# --------------------------------------------------------------------------------------------- #
@application.route("/")
def home():
    try:
       
        total_donors = collection_donor_details.count_documents({})
        total_patients = collection_patient_details.count_documents({})
        total_matches = collection_patient_details.count_documents({'status': 'Donated'})
        
        # Get patient reviews from the database (most recent 3)
        patient_reviews = list(collection_patient_reviews.find().sort('date_submitted', -1).limit(3))
        
        # Get total count of reviews for pagination
        total_reviews = collection_patient_reviews.count_documents({})
        
        # Get testimonials from the database
        testimonials = list(collection_testimonials.find().limit(3))
        
        # Convert ObjectId to string and ensure rating is a float
        for item in patient_reviews + testimonials:
            if '_id' in item:
                item['_id'] = str(item['_id'])
            # Ensure rating is a float
            if 'rating' in item:
                item['rating'] = float(item['rating'])
            # Convert patient_id to string if it exists
            if 'patient_id' in item:
                item['patient_id'] = str(item['patient_id'])
        
        return render_template("home.html", 
                            total_donors=total_donors,
                            total_patients=total_patients,
                            total_matches=total_matches,
                            patient_reviews=patient_reviews,
                            total_reviews=total_reviews,
                            testimonials=testimonials)
    except Exception as e:
        
        print(f"Error in home route: {str(e)}")
        return render_template("home.html", 
                            total_donors=0,
                            total_patients=0,
                            total_matches=0,
                            patient_reviews=[],
                            total_reviews=0,
                            testimonials=[])


# Redirecting to donor.html template. 
# -------------------------------------------------------------------- ----------------------------------#
@application.route('/donor')
def donor():
    return render_template('donor.html')


# Redirecting to patient.html template 
# -------------------------------------------------------------------------------------------------------#
@application.route('/patient')
def patient():
    return render_template('patient_auth.html')


# Redirecting admin.html template 
# -------------------------------------------------------------------------------------------------------- #
@application.route('/admin')
def admin():
    if is_admin_logged_in():
        return redirect(url_for('admin_dashboard'))
    return render_template('admin.html')


# Redirecting for Admin Login 
# --------------------------------------------------------------------------- #
@application.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if is_admin_logged_in():
        return redirect(url_for('admin_dashboard'))
        
    if request.method == 'POST':
        username = request.form['Username']
        password = request.form['password']

        # Verify the user from the database
        user = collection_users_details.find_one({'username': username})
        if user:
            # Ensure password comparison works with bytes
            if bcrypt.checkpw(password.encode('utf-8'), user['password']):
                # Set session variables
                session['admin_logged_in'] = True
                session['admin_username'] = username
                session['admin_id'] = str(user['_id'])
                session['admin_role'] = user.get('role', 'admin')
                session['last_activity'] = datetime.now().isoformat()
                
                flash('Login successful!', 'success')
                # Redirect to the admin dashboard with data
                return redirect(url_for('admin_dashboard'))
            else:
                flash('Invalid password.', 'danger')
        else:
            flash('Username not found.', 'danger')

        return redirect(url_for('admin'))


# Define a function to check if the user is logged in as an admin 
# ----------------------------------------------------------------------------------------------------- #
def is_admin_logged_in():
    return session.get('admin_logged_in', False)




# File Uploads 
# ------------------------------------------------------------------------------------------ #

# Add configuration for file uploads
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
ALLOWED_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png'}

# Create upload directories if they don't exist
try:
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(os.path.join(UPLOAD_FOLDER, 'id_proofs'), exist_ok=True)
    os.makedirs(os.path.join(UPLOAD_FOLDER, 'medical_reports'), exist_ok=True)
except Exception as e:
    print(f"Error creating upload directories: {str(e)}")

application.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
application.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS




# INSERT DATA TO DONAR DATABASE
# ------------------------------------------------------------------------------------------------ #
@application.route('/insert_data', methods=['POST'])
def insert_data():
    try:
        # Handle file uploads
        id_proof = request.files.get('id_proof')
        medical_history_doc = request.files.get('medical_history_doc')

        # Process and store files
        id_proof_data = None
        medical_history_data = None

        if id_proof:
            id_proof_data = {
                'filename': secure_filename(id_proof.filename),
                'data': id_proof.read(),
                'content_type': id_proof.content_type
            }

        if medical_history_doc:
            medical_history_data = {
                'filename': secure_filename(medical_history_doc.filename),
                'data': medical_history_doc.read(),
                'content_type': medical_history_doc.content_type
            }

        # Prepare donor data
        data = {
            "DonarName": request.form['DonarName'],
            "Age": int(request.form['Age']),
            "Gender": request.form['Gender'],
            "address": request.form['address'],
            "BloodGroup": request.form['BloodGroup'],
            "Email": request.form['Email'],
            "Contactnumber": request.form['Contactnumber'],
            "DonateOrgan": request.form['DonateOrgan'],
            "CausesOfDeath": request.form.get('CausesOfDeath', ''),
            "medical_history": request.form.get('medical_history', ''),
            "physician_name": request.form.get('physician_name', ''),
            "physician_contact": request.form.get('physician_contact', ''),
            "emergency_contact": {
                "name": request.form.get('emergency_contact_name', ''),
                "relation": request.form.get('emergency_contact_relation', ''),
                "phone": request.form.get('emergency_contact_phone', ''),
                "address": request.form.get('emergency_contact_address', '')
            },
            "consent": {
                "organ_donation": request.form.get('consent_organ_donation') == 'on',
                "medical_release": request.form.get('consent_medical_release') == 'on',
                "family_notification": request.form.get('consent_family_notification') == 'on',
                "privacy_policy": request.form.get('consent_privacy_policy') == 'on'
            },
            "registration_date": datetime.now(),
            "Status": "OUT",
            "documents": {
                "id_proof": id_proof_data,
                "medical_history": medical_history_data
            }
        }

        # Insert data into MongoDB
        insert_result = collection_donor_details.insert_one(data)

        if insert_result.inserted_id:
            flash('Registration successful! Thank you for your noble decision to donate organs.', 'success')
            return redirect(url_for('get_donor_details'))
        else:
            flash('Registration failed. Please try again.', 'danger')
            return redirect(url_for('get_donor_details'))

    except Exception as e:
        print(f"Error in donor registration: {str(e)}")
        flash(f'An error occurred during registration. Please try again.', 'danger')
        return redirect(url_for('get_donor_details'))

#
# INSERT DATA TO PATIENT DATABASE 
# ------------------------------------------------------------------------------------------------ #
@application.route('/insert_patient', methods=['POST'])
def insert_patient():
    try:
        # Get form data
        fullname = request.form['fullname']
        age = int(request.form['age'])
        gender = request.form['gender']
        address = request.form['address']
        bloodgroup = request.form['bloodgroup']
        email = request.form['email']
        contactnumber = request.form['contactnumber']
        neededorgan = request.form['neededorgan']
        urgency = request.form.get('urgency', 'Standard')
        medical_history = request.form.get('medical_history', '')
        physician_name = request.form.get('physician_name', '')
        physician_contact = request.form.get('physician_contact', '')
        password = request.form['password']
        
        # Hash the password
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        
        # Prepare patient data with consistent field names
        data = {
                "fullname": fullname,
                "age": age,
                "gender": gender,
                "address": address,
                "bloodgroup": bloodgroup,
                "email": email,
                "contactnumber": contactnumber,
                "neededorgan": neededorgan,
                "urgency": urgency,
                "medical_history": medical_history,
                "physician_name": physician_name,
                "physician_contact": physician_contact,
                "password": hashed_password,
                "registration_date": datetime.now(),
                "last_updated": datetime.now(),
                "status": "Waiting"
        }

        # Insert data into MongoDB
        insert_result = collection_patient_details.insert_one(data)

        if insert_result.inserted_id:
                flash('Registration successful! You can now login to your account.', 'success')
                return redirect(url_for('patient'))
        else:
                flash('Registration failed. Please try again.', 'danger')
                return redirect(url_for('patient'))
            
    except Exception as e:
        print(f"Error in patient registration: {str(e)}")
        flash('An error occurred during registration. Please try again.', 'danger')
        return redirect(url_for('patient'))


# CREATE USER
# ------------------------------------------------------------------------------------------------ #
@application.route('/create_user', methods=['GET', 'POST'])
def create_user():
    if request.method == 'POST':
        # Get all form data
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        role = request.form['role']

        # Validate password match
        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('users.html')

        # Check if the username already exists
        existing_user = collection_users_details.find_one({'username': username})
        if existing_user:
            flash('Username already exists. Please choose a different username.', 'danger')
            return render_template('users.html')

        # Check if the email already exists
        existing_email = collection_users_details.find_one({'email': email})
        if existing_email:
            flash('Email already exists. Please use a different email.', 'danger')
            return render_template('users.html')

        # Hash the password before storing it
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        
        # Create user data dictionary
        user_data = {
            'first_name': first_name,
            'last_name': last_name,
            'username': username,
            'email': email,
            'password': hashed_password,
            'role': role,
            'created_at': datetime.now()
        }

        # Insert new user into the database
        try:
            collection_users_details.insert_one(user_data)
            flash('User created successfully!', 'success')
            return redirect(url_for('admin'))
        except Exception as e:
            flash('Error creating user. Please try again.', 'danger')
            return render_template('users.html')

    return render_template('users.html')


# patient details page in admin panel
@application.route("/donor-details")
@admin_required
def get_donor_details():
    donor_data = list(collection_donor_details.find())
    for item in donor_data:
        item['_id'] = str(item['_id'])
    return render_template("donorDetails.html", donor_data=donor_data)

@application.route('/delete-donor', methods=['POST'])
def delete_donor():
    donor_id = request.form.get('donor_id')
    if donor_id:
        try:
            # Convert string ID to ObjectId
            donor_id_obj = ObjectId(donor_id)
            # Delete the donor
            result = collection_donor_details.delete_one({'_id': donor_id_obj})
            if result.deleted_count > 0:
                flash('Donor deleted successfully!', 'success')
            else:
                flash('Failed to delete donor. Donor not found.', 'danger')
        except Exception as e:
            flash(f'Error deleting donor: {str(e)}', 'danger')
    else:
        flash('No donor ID provided.', 'danger')
    
    return redirect(url_for('get_donor_details'))

@application.route('/edit-donor/<donor_id>')
@admin_required
def edit_donor(donor_id):
    try:
        # Convert string ID to ObjectId
        donor_id_obj = ObjectId(donor_id)
        # Find the donor
        donor = collection_donor_details.find_one({'_id': donor_id_obj})
        
        if donor:
            # Convert ObjectId to string for template
            donor['_id'] = str(donor['_id'])
            return render_template('edit_donor.html', donor=donor)
        else:
            flash('Donor not found.', 'danger')
            return redirect(url_for('get_donor_details'))
    except Exception as e:
        flash(f'Error retrieving donor details: {str(e)}', 'danger')
        return redirect(url_for('get_donor_details'))

@application.route('/update-donor/<donor_id>', methods=['POST'])
@admin_required
def update_donor(donor_id):
    try:
        # Convert string ID to ObjectId
        donor_id_obj = ObjectId(donor_id)
        
        # Prepare updated donor data
        updated_data = {
            "DonarName": request.form['DonarName'],
            "Age": int(request.form['Age']),
            "Gender": request.form['Gender'],
            "address": request.form['address'],
            "BloodGroup": request.form['BloodGroup'],
            "Contactnumber": request.form['Contactnumber'],
            "DonateOrgan": request.form['DonateOrgan'],
            "CausesOfDeath": request.form.get('CausesOfDeath', ''),
            "medical_history": request.form.get('medical_history', ''),
            "physician_name": request.form.get('physician_name', ''),
            "physician_contact": request.form.get('physician_contact', ''),
            "Status": request.form['Status']
        }
        
        # Update the donor
        result = collection_donor_details.update_one(
            {'_id': donor_id_obj},
            {'$set': updated_data}
        )
        
        if result.modified_count > 0:
            flash('Donor details updated successfully!', 'success')
        else:
            flash('No changes made to donor details.', 'info')
        
        return redirect(url_for('get_donor_details'))
    except Exception as e:
        flash(f'Error updating donor details: {str(e)}', 'danger')
        return redirect(url_for('edit_donor', donor_id=donor_id))
    



# patient details page in admin panel
@application.route("/patient-details")
@admin_required
def get_patient_details():
    patient_data = list(collection_patient_details.find())
    for item in patient_data:
        item['_id'] = str(item['_id'])
    return render_template("patientDetails.html", patient_data=patient_data)


# delete patient from patient details page in admin panel
@application.route('/delete-patient', methods=['POST'])
@admin_required
def delete_patient():
    if request.method == 'POST':
        patient_id = request.form.get('patient_id')
        # Delete the donor entry based on the patient_id
        collection_patient_details.delete_one({'_id': ObjectId(patient_id)})
    return redirect(url_for('get_patient_details'))


# edit patient from patient details page in admin pa
@application.route('/edit-patient/<patient_id>', methods=['GET', 'POST'])
@admin_required
def edit_patient(patient_id):
    # Get patient data
    patient = collection_patient_details.find_one({'_id': ObjectId(patient_id)})
    
    if not patient:
        flash('Patient record not found.', 'danger')
        return redirect(url_for('get_patient_details'))
    
    if request.method == 'POST':
        # Get form data
        fullname = request.form['fullname']
        age = int(request.form['age'])
        gender = request.form['gender']
        address = request.form['address']
        bloodgroup = request.form['bloodgroup']
        contactnumber = request.form['contactnumber']
        neededorgan = request.form['neededorgan']
        urgency = request.form.get('urgency', 'Standard')
        status = request.form.get('status', 'Waiting')  # Get status from form with default value
        medical_history = request.form.get('medical_history', '')
        physician_name = request.form.get('physician_name', '')
        physician_contact = request.form.get('physician_contact', '')
        
        # Check if urgency level changed
        urgency_changed = patient.get('urgency') != urgency
        status_changed = patient.get('status') != status
        
        # Update patient data
        update_data = {
            "fullname": fullname,
            "age": age,
            "gender": gender,
            "address": address,
            "bloodgroup": bloodgroup,
            "contactnumber": contactnumber,
            "neededorgan": neededorgan,
            "urgency": urgency,
            "status": status,
            "medical_history": medical_history,
            "physician_name": physician_name,
            "physician_contact": physician_contact,
            "last_updated": datetime.now()
        }
        
        # Update in database
        collection_patient_details.update_one(
            {'_id': ObjectId(patient_id)},
            {'$set': update_data}
        )
        
        # Create timeline event if urgency changed
        if urgency_changed:
            timeline_event = {
                "patient_id": ObjectId(patient_id),
                "date": datetime.now(),
                "title": "Urgency Level Updated",
                "description": f"Your urgency level has been updated from {patient.get('urgency')} to {urgency}."
            }
            collection_timeline.insert_one(timeline_event)
        
        # Create timeline event if status changed
        if status_changed:
            timeline_event = {
                "patient_id": ObjectId(patient_id),
                "date": datetime.now(),
                "title": "Status Updated",
                "description": f"Your status has been updated from {patient.get('status')} to {status}."
            }
            collection_timeline.insert_one(timeline_event)
            
        flash('Patient details updated successfully.', 'success')
        return redirect(url_for('get_patient_details'))
    
    # Convert ObjectId to string for template
    patient['_id'] = str(patient['_id'])
    
    # GET request - show the form
    return render_template('edit_patient.html', patient=patient)



#  Redirecting to organ-donate-process
@application.route('/organ-donate-process')
@admin_required
def organDonateProcess():
    donor_data = list(collection_donor_details.find())
    # Convert ObjectId to string representation
    for item in donor_data:
        item['_id'] = str(item['_id'])
    return render_template("organDonateProcess.html", donor_data=donor_data)

# Function to check blood group compatibility
def is_blood_compatible(donor_blood, recipient_blood):
    # Blood compatibility chart
    compatibility = {
        "O-": ["O-", "O+", "A-", "A+", "B-", "B+", "AB-", "AB+"],  # O- can donate to anyone
        "O+": ["O+", "A+", "B+", "AB+"],  # O+ can donate to any positive
        "A-": ["A-", "A+", "AB-", "AB+"],  # A- can donate to A and AB
        "A+": ["A+", "AB+"],  # A+ can donate to A+ and AB+
        "B-": ["B-", "B+", "AB-", "AB+"],  # B- can donate to B and AB
        "B+": ["B+", "AB+"],  # B+ can donate to B+ and AB+
        "AB-": ["AB-", "AB+"],  # AB- can donate to AB
        "AB+": ["AB+"]  # AB+ can donate only to AB+
    }
    
    # Check if donor blood group can donate to recipient
    if donor_blood in compatibility and recipient_blood in compatibility[donor_blood]:
        return True
    return False

@application.route('/organ-process-form', methods=['POST'])
def organ_donate_process():
    if request.method == 'POST':
        donor_id = request.form.get('donor_id')
        action = request.form.get('action')

        try:
            donor = collection_donor_details.find_one({'_id': ObjectId(donor_id)})
            if donor:
                # If action is to set status to OUT, we need to check if there's a match first
                if action == "OUT":
                    # Find matching patients who need the organ that the donor is donating
                    potential_matches = list(collection_patient_details.find({
                        '$or': [
                            {'NeededOrgan': donor['DonateOrgan'], 'Status': 'Waiting'},
                            {'neededorgan': donor['DonateOrgan'], 'status': 'Waiting'}
                        ]
                    }))
                    
                    # Filter by blood group compatibility
                    compatible_matches = []
                    for patient in potential_matches:
                        # Get blood group, handling both field name formats
                        patient_blood = patient.get('BloodGroup', patient.get('bloodgroup', ''))
                        if is_blood_compatible(donor['BloodGroup'], patient_blood):
                            compatible_matches.append(patient)
                    
                    if not compatible_matches:
                        # No compatible match found, keep status as "IN"
                        flash(f"Cannot set status to OUT. No compatible patient found for {donor['DonateOrgan']} with blood group {donor['BloodGroup']}. Status remains IN.", 'warning')
                        return redirect(url_for('organDonateProcess'))
                    
                    # If we have compatible matches, proceed with the donation process
                    matching_patient = compatible_matches[0]
                        
                    # Update patient status to Donated - update both field name formats
                    collection_patient_details.update_one({'_id': matching_patient['_id']}, 
                        {'$set': {
                            'Status': 'Donated',
                            'status': 'Donated'
                        }})
                        
                    # Update donor status to OUT (donated)
                    collection_donor_details.update_one(
                        {'_id': ObjectId(donor_id)}, 
                        {'$set': {'Status': 'OUT'}}
                    )
                        
                    # Get patient name, handling both field name formats
                    patient_name = matching_patient.get('Patientname', matching_patient.get('fullname', 'Unknown'))
                        
                    # Get patient blood group, handling both field name formats
                    patient_blood = matching_patient.get('BloodGroup', matching_patient.get('bloodgroup', 'Unknown'))
                        
                    # Get needed organ, handling both field name formats
                    needed_organ = matching_patient.get('NeededOrgan', matching_patient.get('neededorgan', donor['DonateOrgan']))
                    
                    # Create a timeline event for the patient
                    timeline_event = {
                        "patient_id": matching_patient['_id'],
                        "date": datetime.now(),
                        "title": "Organ Match Found",
                        "description": f"A matching {donor['DonateOrgan']} with compatible blood group {donor['BloodGroup']} has been found for you. Your status has been updated to 'Donated'.",
                        "category": "status_update"
                    }
                    collection_timeline.insert_one(timeline_event)
                        
                    # Create a match record
                    match_data = {
                        "donor_id": donor['_id'],
                        "donor_name": donor['DonarName'],
                        "patient_id": matching_patient['_id'],
                        "patient_name": patient_name,
                        "organ_type": donor['DonateOrgan'],
                        "donor_blood": donor['BloodGroup'],
                        "recipient_blood": patient_blood,
                        "match_date": datetime.now(),
                        "status": "matched"
                    }
                    collection_matches.insert_one(match_data)
                            
                    flash(f"Donor status updated to OUT (donated). A matching patient ({patient_name}) with compatible blood group has been found and their status has been updated to 'Donated'.", 'success')
                else:
                    # If action is to set status to IN, prevent this action
                    flash(f"Cannot change status from OUT to IN directly. Once a donation is completed, it cannot be reversed.", 'warning')
                
                return redirect(url_for('organDonateProcess'))
            else:
                flash("Donor not found.", 'danger')
                return redirect(url_for('organDonateProcess'))
        except Exception as e:
            flash(f"An error occurred: {str(e)}", 'danger')
            return redirect(url_for('organDonateProcess'))
    
    return redirect(url_for('organDonateProcess'))

@application.route('/donated-patient')
@admin_required
def donated_patients():
    # Query for patients with status 'Donated' using the correct field name
    patient_data = list(collection_patient_details.find({'status': 'Donated'}))

    # Convert ObjectId to string representation
    for item in patient_data:
        item['_id'] = str(item['_id'])
    
    return render_template("donatedPatient.html", patient_data=patient_data)


@application.route('/not-donated-patient')
@admin_required
def not_donated_patients():
    # Query for patients with status 'Waiting' using the correct field name
    patient_data = list(collection_patient_details.find({'status': 'Waiting'}))
    
    # Convert ObjectId to string representation
    for item in patient_data:
        item['_id'] = str(item['_id'])
    
    return render_template("notDonatedPatient.html", patient_data=patient_data)

# Redirecting the query
@application.route('/submit_query', methods=['POST'])
def submit_query():
    query = {
        "full_name": request.form['full_name'],
        "phone_number": request.form['phone_number'],
        "email": request.form['email'],
        "message": request.form['message'],
        "submission_date": datetime.now(),
        "status": "Pending",
        "assigned_doctor": None,
        "assignment_date": None
    }

    # Insert data into MongoDB
    insert_result = collection_users_query.insert_one(query)
    if insert_result.inserted_id:
        flash('Your query has been submitted successfully. A doctor will be assigned to assist you.', 'success')
        return redirect(url_for('home'))
    else:
        flash('Failed to submit query. Please try again.', 'error')
        return redirect(url_for('home'))

# Redirecting the query
@application.route('/query')
def get_query():
    queries = list(collection_users_query.find())
    for item in queries:
        item['_id'] = str(item['_id'])
    return render_template("query.html", queries = queries)

# Redirecting to logout.html
@application.route('/logout')
def logout():
    # Clear all session data
    session.clear()
    flash('Logout successful.', 'danger')
    return redirect(url_for('admin'))

# Chatbot routes
@application.route('/chatbot')
def chatbot():
    return render_template('chatbot.html')

def load_context_from_file(filename):
    try:
        with open(filename, 'r', encoding='utf-8') as file:
            return file.read()
    except Exception as e:
        print(f"Error reading context file: {e}")
        return None

@application.route('/ask', methods=['POST'])
def ask_question():
    try:
        data = request.json
        question = data.get('question')
        context = data.get('context', '')
        
        if not question:
            return jsonify({'error': 'Question is required'}), 400
            
        if not context:
            # Load default context from file
            default_context = load_context_from_file('Chatbot/context/organ_donation_context.txt')
            if default_context is None:
                return jsonify({'error': 'Could not load context file'}), 500
            context = default_context
        
        # Get the model and generate an answer
        qa_model = get_qa_model()
        answer = qa_model(context=context, question=question)
        
        return jsonify({'answer': answer['answer']})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@application.route('/submit_feedback', methods=['POST'])
def submit_feedback():
    try:
        data = request.json
        rating = data.get('rating', 0)
        feedback_text = data.get('feedback', '')
        
        if not rating and not feedback_text:
            return jsonify({'error': 'Rating or feedback text is required'}), 400
            
        # Prepare feedback data
        feedback_data = {
            "rating": rating,
            "feedback": feedback_text,
            "timestamp": datetime.now()
        }
        
        # Insert data into MongoDB
        insert_result = collection_chatbot_feedback.insert_one(feedback_data)
        
        if insert_result.inserted_id:
            return jsonify({'success': True, 'message': 'Feedback submitted successfully'})
        else:
            return jsonify({'error': 'Failed to submit feedback'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Patient required decorator
# ----------------------------------------------------------------------------------------------------- #
def patient_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_patient_logged_in():
            flash('Access denied. Patient login required.', 'error')
            return redirect(url_for('patient'))
        return f(*args, **kwargs)
    return decorated_function

# PATIENT LOGIN
# ------------------------------------------------------------------------------------------------ #
@application.route('/patient_login', methods=['GET', 'POST'])
def patient_login():
    if is_patient_logged_in():
        return redirect(url_for('patient_dashboard'))
        
    if request.method == 'POST':
        try:
            email = request.form['email']
            password = request.form['password']

            # Find patient
            patient = collection_patient_details.find_one({'email': email})
            
            if patient and bcrypt.checkpw(password.encode('utf-8'), patient['password']):
                # Set session variables
                session['patient_logged_in'] = True
                session['patient_id'] = str(patient['_id'])
                session['patient_email'] = patient['email']
                session['patient_name'] = patient['fullname']
                
                flash('Login successful!', 'success')
                return redirect(url_for('patient_dashboard'))
            else:
                if patient:
                    flash('Invalid password. Please try again.', 'danger')
                else:
                    flash('Email not found. Please try again.', 'danger')
                return redirect(url_for('patient'))
        except Exception as e:
            print(f"Error during login: {str(e)}")
            flash('An error occurred during login. Please try again.', 'danger')
            return redirect(url_for('patient'))
    
    # If it's a GET request, redirect to the combined patient page
    return redirect(url_for('patient'))


# Define a function to check if the user is logged in as a patient
# ----------------------------------------------------------------------------------------------------- #
def is_patient_logged_in():
    return session.get('patient_logged_in', False)


# Calculate days on waitlist
def calculate_days_on_waitlist(registration_date):
    if not registration_date:
        return 0
    
    # Ensure both datetimes are timezone naive
    if registration_date.tzinfo is not None:
        # Convert to naive datetime if it has timezone info
        registration_date = registration_date.replace(tzinfo=None)
    
    today = datetime.now()
    delta = today - registration_date
    return delta.days

# Calculate position on waitlist based on priority
def calculate_waitlist_position(patient_id, organ_type, urgency, registration_date):
    """Calculate the patient's position on the waitlist based on urgency and registration date"""
    if not registration_date:
        return 0
    
    # Ensure registration_date is timezone naive
    if registration_date.tzinfo is not None:
        registration_date = registration_date.replace(tzinfo=None)
    
    # Define urgency levels and their weights
    urgency_weights = {
        'Critical': 4,
        'Urgent': 3,
        'Standard': 2,
        'Elective': 1
    }
    
    # Get current patient's urgency weight
    current_urgency_weight = urgency_weights.get(urgency, 2)  # Default to Standard if not found
    
    # Find all patients waiting for the same organ
    waiting_patients = list(collection_patient_details.find({
        'neededorgan': organ_type,
        'status': 'Waiting',
        '_id': {'$ne': ObjectId(patient_id)}  # Exclude current patient
    }))
    
    # Count patients with higher priority
    higher_priority_count = 0
    for patient in waiting_patients:
        patient_urgency = patient.get('urgency', 'Standard')
        patient_urgency_weight = urgency_weights.get(patient_urgency, 2)
        patient_reg_date = patient.get('registration_date')
        
        # Ensure patient_reg_date is timezone naive for comparison
        if patient_reg_date and patient_reg_date.tzinfo is not None:
            patient_reg_date = patient_reg_date.replace(tzinfo=None)
        
        # Higher urgency level gets priority
        if patient_urgency_weight > current_urgency_weight:
            higher_priority_count += 1
        # Same urgency level, earlier registration date gets priority
        elif patient_urgency_weight == current_urgency_weight and patient_reg_date and patient_reg_date < registration_date:
            higher_priority_count += 1
    
    # Position is 1-indexed (position 1 is first in line)
    return higher_priority_count + 1

# Routes for patient registration and login
@application.route('/patient_register')
def patient_register():
    return redirect(url_for('patient', form='register'))


# patient registration from patient personal page as well as admin panel
@application.route('/register_patient', methods=['POST'])
def register_patient():
    if request.method == 'POST':
        try:
            # Get form data
            email = request.form['email']
            password = request.form['password']
            confirm_password = request.form.get('confirm_password', '')
            
            # Validate passwords match (though this is also checked by JavaScript)
            if password != confirm_password:
                flash('Passwords do not match. Please try again.', 'danger')
                return redirect(url_for('patient', form='register'))
            
            fullname = request.form['fullname']
            age = int(request.form['age'])
            gender = request.form['gender']
            address = request.form['address']
            bloodgroup = request.form['bloodgroup']
            contactnumber = request.form['contactnumber']
            neededorgan = request.form['neededorgan']
            urgency = request.form['urgency']
            medical_history = request.form.get('medical_history', '')
            physician_name = request.form.get('physician_name', '')
            physician_contact = request.form.get('physician_contact', '')
         
            
            # Check if email already exists - check both uppercase and lowercase field names
            existing_patient = collection_patient_details.find_one({
                '$or': [
                    {'Email': email},
                    {'email': email}
                ]
            })
            
            if existing_patient:
                flash('Email already registered. Please use a different email or login to your account.', 'danger')
                return redirect(url_for('patient', form='register'))
            
            # Hash password
            hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            print(f"Password type after hashing: {type(hashed_password)}")
            
            # Registration date
            registration_date = datetime.now()
            
            # Prepare patient data - use both uppercase and lowercase field names for compatibility
            patient_data = {
                # Use both field name formats for compatibility
                "Email": email,
                "email": email,
                "password": hashed_password,
                "Patientname": fullname,
                "fullname": fullname,
                "Age": age,
                "age": age,
                "Gender": gender,
                "gender": gender,
                "address": address,
                "BloodGroup": bloodgroup,
                "bloodgroup": bloodgroup,
                "Contactnumber": contactnumber,
                "contactnumber": contactnumber,
                "NeededOrgan": neededorgan,
                "neededorgan": neededorgan,
                "Timereqired": urgency,
                "urgency": urgency,
                "medical_history": medical_history,
                "physician_name": physician_name,
                "physician_contact": physician_contact,
                "Status": "Waiting",
                "status": "Waiting",
                "registration_date": registration_date,
                "last_updated": registration_date
            }
            
            # Insert into database
            patient_id = collection_patient_details.insert_one(patient_data).inserted_id
            # Verify the patient was inserted correctly
            inserted_patient = collection_patient_details.find_one({'_id': patient_id})
    
            
            # Create initial timeline event
            timeline_event = {
                "patient_id": patient_id,
                "date": registration_date,
                "title": "Registration Completed",
                "description": f"You have been registered for {neededorgan} transplant with {urgency} urgency level."
            }
            collection_timeline.insert_one(timeline_event)
            
            # Create welcome notification
            notification = {
                "patient_id": patient_id,
                "date": registration_date,
                "message": f"Welcome to the Organ Donation System. Your registration for {neededorgan} has been recorded."
            }
            collection_notifications.insert_one(notification)
            
            flash('Registration successful! You can now login to your account.', 'success')
            return redirect(url_for('patient'))
        
        except Exception as e:
            print(f"Error during patient registration: {str(e)}")
            flash(f'Registration failed. Please try again later.', 'danger')
            return redirect(url_for('patient', form='register'))
    
    return redirect(url_for('patient', form='register'))



# patient dashboard from patient personal page
@application.route('/patient_dashboard')
@patient_required
def patient_dashboard():
    try:
        # Get patient ID from session
        patient_id = session.get('patient_id')
        
        # Get patient data
        patient = collection_patient_details.find_one({'_id': ObjectId(patient_id)})
        
        if not patient:
            session.clear()
            flash('Patient record not found. Please login again.', 'danger')
            return redirect(url_for('patient'))
        
        # Get patient's review if it exists
        patient_review = collection_patient_reviews.find_one({'patient_id': patient_id})
        if patient_review:
            patient_review['_id'] = str(patient_review['_id'])
        
        # Get patient's timeline events
        timeline = list(collection_timeline.find({'patient_id': ObjectId(patient_id)}).sort('date', -1))
        for event in timeline:
            event['_id'] = str(event['_id'])
            # Format date for display
            if 'date' in event:
                event['date'] = event['date'].strftime('%d %b %Y')
        
        # Get patient's notifications
        notifications = list(collection_notifications.find({'patient_id': ObjectId(patient_id)}).sort('date', -1))
        for notification in notifications:
            notification['_id'] = str(notification['_id'])
            # Format date for display
            if 'date' in notification:
                notification['date'] = notification['date'].strftime('%d %b %Y')
        
        # Check if review was just submitted (from query parameter)
        review_submitted = request.args.get('review_submitted', False)
        
        # Calculate days on waitlist
        registration_date = patient.get('registration_date')
        days_on_waitlist = calculate_days_on_waitlist(registration_date) if registration_date else 0
        
        # Get organ type
        organ_type = patient.get('neededorgan', '')
        
        # Get urgency level
        urgency = patient.get('urgency', 'Standard')
        
        # Get status
        status = patient.get('status', 'Waiting')
        
        # Calculate waitlist position
        waitlist_position = calculate_waitlist_position(patient_id, organ_type, urgency, registration_date)
        
        # Get total count of patients waiting for the same organ
        waitlist_count = collection_patient_details.count_documents({
            'neededorgan': organ_type, 
            'status': 'Waiting'
        })
        
        # Prepare patient data for template
        patient_data = {
            '_id': patient_id,
            'fullname': patient.get('fullname', ''),
            'age': patient.get('age', ''),
            'gender': patient.get('gender', ''),
            'bloodgroup': patient.get('bloodgroup', ''),
            'contactnumber': patient.get('contactnumber', ''),
            'email': patient.get('email', ''),
            'neededorgan': organ_type,
            'status': status,
            'days_on_waitlist': days_on_waitlist,
            'urgency': urgency,
            'position': waitlist_position,
            'medical_history': patient.get('medical_history', ''),
            'physician_name': patient.get('physician_name', ''),
            'physician_contact': patient.get('physician_contact', '')
        }
        
        print("Rendering patient_dashboard.html with data:", patient_data)
        return render_template('patient_dashboard.html', 
                            patient=patient_data, 
                            waitlist_count=waitlist_count,
                            patient_review=patient_review,
                            review_submitted=review_submitted,
                            timeline=timeline,
                            notifications=notifications)
    except Exception as e:
        print(f"Error in patient dashboard: {str(e)}")
        session.clear()
        flash('An error occurred. Please login again.', 'danger')
        return redirect(url_for('patient'))

# patient logout from patient dashboard
@application.route('/patient_logout')
def patient_logout():
    # Clear session variables
    session.pop('patient_logged_in', None)
    session.pop('patient_id', None)
    session.pop('patient_email', None)
    session.pop('patient_name', None)
    
    flash('You have been logged out successfully.', 'success')
    return redirect(url_for('patient'))


# patient update from patient dashboard
@application.route('/patient_update', methods=['GET', 'POST'])
def patient_update():
    # Get patient ID from session
    patient_id = session.get('patient_id')
    
    # Get patient data
    patient = collection_patient_details.find_one({'_id': ObjectId(patient_id)})
    
    if not patient:
        flash('Patient record not found.', 'danger')
        return redirect(url_for('patient_dashboard'))
    
    if request.method == 'POST':
        try:
            # Get form data
            contactnumber = request.form['contactnumber']
            address = request.form['address']
            medical_history = request.form.get('medical_history', '')
            physician_name = request.form.get('physician_name', '')
            physician_contact = request.form.get('physician_contact', '')
            
                # Update patient data
            update_data = {
                "contactnumber": contactnumber,
                    "address": address,
                "medical_history": medical_history,
                "physician_name": physician_name,
                "physician_contact": physician_contact,
                "last_updated": datetime.now()
            }
            
            # Update in database
            collection_patient_details.update_one(
                    {'_id': ObjectId(patient_id)},
                {'$set': update_data}
            )
            
            flash('Your information has been updated successfully.', 'success')
            return redirect(url_for('   '))
        except Exception as e:
            print(f"Error in patient update: {str(e)}")
            flash('An error occurred while updating your information. Please try again.', 'danger')
            return redirect(url_for('patient_update'))
    
    # GET request - show the form
    return render_template('patient_update.html', patient=patient)

@application.route('/admin_panel')
@admin_required
def admin_dashboard():
    try:
        # Get current date for the dashboard header
        now = datetime.now()
        
        # Get total counts
        total_donors = collection_donor_details.count_documents({})
        total_patients = collection_patient_details.count_documents({})
        total_matches = collection_patient_details.count_documents({'status': 'Donated'}) + collection_patient_details.count_documents({'Status': 'Donated'})
        pending_requests = collection_patient_details.count_documents({'status': 'Waiting'}) + collection_patient_details.count_documents({'Status': 'Waiting'})
        
        # Get recent donors (last 5)
        recent_donors = list(collection_donor_details.find().sort('_id', -1).limit(5))
        
        # Get recent patients (last 5)
        recent_patients = list(collection_patient_details.find().sort('_id', -1).limit(5))
    
            # Get urgent patients (patients with urgency field set to Critical or Urgent)
            # Handle field name inconsistency by using $or query
        urgent_patients = list(collection_patient_details.find({
            '$or': [
                {'status': 'Waiting', 'urgency': {'$in': ['Critical', 'Urgent']}},
                {'Status': 'Waiting', 'urgency': {'$in': ['Critical', 'Urgent']}}
            ]
        }).sort('_id', 1).limit(5))
        
        # If no urgent patients found, get patients waiting the longest
        if not urgent_patients:
            urgent_patients = list(collection_patient_details.find({
                '$or': [
                    {'status': 'Waiting'},
                    {'Status': 'Waiting'}
                ]
            }).sort('_id', 1).limit(5))
    
        # Get recent matches
        recent_matches = list(collection_patient_details.find({
            '$or': [
                {'status': 'Donated'},
                {'Status': 'Donated'}
            ]
        }).sort('_id', -1).limit(5))
    
        # Convert ObjectId to string for all lists
        for item in recent_donors + recent_patients + urgent_patients + recent_matches:
            item['_id'] = str(item['_id'])
                    
            # Normalize field names for consistency in the template
            for patient in urgent_patients + recent_patients + recent_matches:
                # Ensure all patients have consistent field names
                if 'Status' in patient and 'status' not in patient:
                    patient['status'] = patient['Status']
                if 'NeededOrgan' in patient and 'neededorgan' not in patient:
                    patient['neededorgan'] = patient['NeededOrgan']
        
        return render_template('adminPanel.html',
                                    now=now,
                            total_donors=total_donors,
                            total_patients=total_patients,
                            total_matches=total_matches,
                            pending_requests=pending_requests,
                            recent_donors=recent_donors,
                            recent_patients=recent_patients,
                            urgent_patients=urgent_patients,
                            recent_matches=recent_matches)
    except Exception as e:
        print(f"Error in admin dashboard: {str(e)}")
        flash('An error occurred while loading the dashboard.', 'danger')
        return redirect(url_for('admin'))

@application.route('/match-history')
@admin_required
def match_history():
    # Get all match records
    matches = list(collection_matches.find().sort('match_date', -1))
    
    # Convert ObjectId to string representation
    for match in matches:
        match['_id'] = str(match['_id'])
        if isinstance(match.get('donor_id'), ObjectId):
            match['donor_id'] = str(match['donor_id'])
        if isinstance(match.get('patient_id'), ObjectId):
            match['patient_id'] = str(match['patient_id'])
    
    return render_template('match_history.html', matches=matches)

# Testimonials management routes
@application.route('/testimonials')
@admin_required
def manage_testimonials():
    testimonials = list(collection_testimonials.find())
    for item in testimonials:
        item['_id'] = str(item['_id'])
    return render_template('testimonials.html', testimonials=testimonials)

# Adding the testimonial
@application.route('/add_testimonial', methods=['POST'])
@admin_required
def add_testimonial():
    try:
        testimonial = {
            "name": request.form['name'],
            "role": request.form['role'],
            "text": request.form['text'],
            "rating": float(request.form['rating']),
            "image": request.form.get('image', ''),
            "date_added": datetime.now()
        }
        
        insert_result = collection_testimonials.insert_one(testimonial)
        if insert_result.inserted_id:
            return redirect(url_for('manage_testimonials'))
        else:
            return "Failed to add testimonial"
    except ValueError:
        # Handle case where rating is not a valid float
        return "Error: Rating must be a valid number"
    except Exception as e:
        return f"Error adding testimonial: {str(e)}"

# Editing the testimonial
@application.route('/edit_testimonial/<testimonial_id>', methods=['POST'])
@admin_required
def edit_testimonial(testimonial_id):
    try:
        updated_testimonial = {
            "name": request.form['name'],
            "role": request.form['role'],
            "text": request.form['text'],
            "rating": float(request.form['rating']),
            "image": request.form.get('image', ''),
            "date_updated": datetime.now()
        }
        
        result = collection_testimonials.update_one(
            {'_id': ObjectId(testimonial_id)},
            {'$set': updated_testimonial}
        )
        
        if result.modified_count > 0:
            return redirect(url_for('manage_testimonials'))
        else:
            return "Failed to update testimonial"
    except ValueError:
        # Handle case where rating is not a valid float
        return "Error: Rating must be a valid number"
    except Exception as e:
        return f"Error updating testimonial: {str(e)}"

# Deleting the testimonial
@application.route('/delete_testimonial/<testimonial_id>')
@admin_required
def delete_testimonial(testimonial_id):
    result = collection_testimonials.delete_one({'_id': ObjectId(testimonial_id)})
    if result.deleted_count > 0:
        return redirect(url_for('manage_testimonials'))
    else:
        return "Failed to delete testimonial"


# Submitting the patient review
@application.route('/submit_patient_review', methods=['POST'])
@patient_required
def submit_patient_review():
    try:
        # Get patient info
        patient_id = session.get('patient_id')
        patient = collection_patient_details.find_one({'_id': ObjectId(patient_id)})
        
        if not patient:
            return "Patient not found", 404
        
        # Check if patient has already submitted a review
        existing_review = collection_patient_reviews.find_one({'patient_id': patient_id})
        
        review_data = {
            "patient_id": patient_id,
            "patient_name": patient.get('fullname', ''),
            "rating": float(request.form['rating']),
            "review_text": request.form['review_text'],
            "date_submitted": datetime.now()
        }
        
        if existing_review:
            # Update existing review
            result = collection_patient_reviews.update_one(
                {'patient_id': patient_id},
                {'$set': {
                    'rating': review_data['rating'],
                    'review_text': review_data['review_text'],
                    'date_updated': datetime.now()
                }}
            )
            success = result.modified_count > 0
        else:
            # Insert new review
            result = collection_patient_reviews.insert_one(review_data)
            success = result.inserted_id is not None
        
        if success:
            return redirect(url_for('patient_dashboard', review_submitted=True))
        else:
            return "Failed to submit review", 500
            
    except Exception as e:
        print(f"Error submitting patient review: {str(e)}")
        return "An error occurred while submitting your review", 500

# Getting more reviews
@application.route('/get_more_reviews')
def get_more_reviews():
    try:
        # Get page number from query parameter, default to 1
        page = int(request.args.get('page', 1))
        per_page = 3
        skip = (page - 1) * per_page
        
        # Get patient reviews from the database
        patient_reviews = list(collection_patient_reviews.find().sort('date_submitted', -1).skip(skip).limit(per_page))
        
        # Convert ObjectId to string and ensure rating is a float
        for item in patient_reviews:
            if '_id' in item:
                item['_id'] = str(item['_id'])
            # Ensure rating is a float
            if 'rating' in item:
                item['rating'] = float(item['rating'])
            # Convert patient_id to string if it exists
            if 'patient_id' in item:
                item['patient_id'] = str(item['patient_id'])
            # Format date
            if 'date_submitted' in item:
                item['date_submitted'] = item['date_submitted'].strftime('%d %b %Y')
        
        return jsonify({
            'reviews': patient_reviews,
            'has_more': len(patient_reviews) == per_page
        })
    except Exception as e:
        print(f"Error fetching more reviews: {str(e)}")
        return jsonify({'error': str(e)}), 500


# Add these new routes for contact management
@application.route('/contact_management')
@admin_required
def contact_management():
   
    queries = list(collection_users_query.find())
    doctors = list(collection_doctors.find())
    
    # Convert ObjectId to string for each query and doctor
    for query in queries:
        query['_id'] = str(query['_id'])
    
    for doctor in doctors:
        doctor['_id'] = str(doctor['_id'])
    
    return render_template('contact_management.html', queries=queries, doctors=doctors)

# Assigning the doctor to the query
@application.route('/assign_doctor', methods=['POST'])
@admin_required
def assign_doctor():
    try:
        query_id = request.form.get('query_id')
        doctor_name = request.form.get('doctor_name')
        
        if not query_id or not doctor_name:
            flash('Missing required information', 'error')
            return redirect(url_for('contact_management'))
        
        # Update the query with assigned doctor
        result = collection_users_query.update_one(
            {'_id': ObjectId(query_id)},
            {
                '$set': {
                    'assigned_doctor': doctor_name,
                    'assignment_date': datetime.now(),
                    'status': 'Assigned'
                }
            }
        )
        
        if result.modified_count > 0:
            flash(f'Successfully assigned {doctor_name} to the query', 'success')
        else:
            flash('Failed to assign doctor', 'error')
            
        return redirect(url_for('contact_management'))
        
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
        return redirect(url_for('contact_management'))


# Adding the doctor to the database
@application.route('/add_doctor', methods=['POST'])
@admin_required
def add_doctor():
    try:
        doctor_name = request.form.get('doctor_name')
        specialization = request.form.get('specialization')
        contact_number = request.form.get('contact_number')
        email = request.form.get('email')
        
        if not doctor_name or not specialization or not contact_number or not email:
            flash('All fields are required', 'error')
            return redirect(url_for('contact_management'))
        
        # Insert the new doctor into the database
        result = collection_doctors.insert_one({
            'name': doctor_name,
            'specialization': specialization,
            'contact_number': contact_number,
            'email': email,
            'date_added': datetime.now()
        })
        
        if result.inserted_id:
            flash(f'Successfully added doctor: {doctor_name}', 'success')
        else:
            flash('Failed to add doctor', 'error')
            
        return redirect(url_for('contact_management'))
        
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
        return redirect(url_for('contact_management'))

# Editing the doctor from the database
@application.route('/edit_doctor/<doctor_id>', methods=['GET', 'POST'])
@admin_required
def edit_doctor(doctor_id):
    try:
        if request.method == 'POST':
            doctor_name = request.form.get('doctor_name')
            specialization = request.form.get('specialization')
            contact_number = request.form.get('contact_number')
            email = request.form.get('email')
            
            if not doctor_name or not specialization or not contact_number or not email:
                flash('All fields are required', 'error')
                return redirect(url_for('edit_doctor', doctor_id=doctor_id))
            
            # Update the doctor in the database
            result = collection_doctors.update_one(
                {'_id': ObjectId(doctor_id)},
                {
                    '$set': {
                        'name': doctor_name,
                        'specialization': specialization,
                        'contact_number': contact_number,
                        'email': email,
                        'last_updated': datetime.now()
                    }
                }
            )
            
            if result.modified_count > 0:
                flash(f'Successfully updated doctor: {doctor_name}', 'success')
                return redirect(url_for('contact_management'))
            else:
                flash('No changes made or doctor not found', 'warning')
                return redirect(url_for('contact_management'))
        else:
            # GET request - show the edit form
            doctor = collection_doctors.find_one({'_id': ObjectId(doctor_id)})
            if doctor:
                doctor['_id'] = str(doctor['_id'])
                return render_template('edit_doctor.html', doctor=doctor)
            else:
                flash('Doctor not found', 'error')
                return redirect(url_for('contact_management'))
            
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
        return redirect(url_for('contact_management'))


# Deleting the doctor from the database
@application.route('/delete_doctor/<doctor_id>')
@admin_required
def delete_doctor(doctor_id):
    try:
        # Delete the doctor from the database
        result = collection_doctors.delete_one({'_id': ObjectId(doctor_id)})
        
        if result.deleted_count > 0:
            flash('Doctor successfully deleted', 'success')
        else:
            flash('Doctor not found', 'error')
            
        return redirect(url_for('contact_management'))
        
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
        return redirect(url_for('contact_management'))

# Viewing the documents of the donors
@admin_required
@application.route('/view_document/<donor_id>/<doc_type>')
def view_document(donor_id, doc_type):
    try:
        donor = collection_donor_details.find_one({'_id': ObjectId(donor_id)})
        if not donor or 'documents' not in donor:
            return "Document not found", 404

        document = donor['documents'].get(doc_type)
        if not document or not document.get('data'):
            return "Document not found", 404

        response = application.response_class(
            document['data'],
            mimetype=document['content_type']
        )
        response.headers.set('Content-Disposition', 'inline', filename=document['filename'])
        return response

    except Exception as e:
        print(f"Error retrieving document: {str(e)}")
        return "Error retrieving document", 500



# For running the application
if __name__ == '__main__':
    application.run(debug=True)


