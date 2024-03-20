import tensorflow as tf
import numpy as np
import cv2
from flask import Flask, render_template,request, redirect, jsonify, url_for, session,flash
import os
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
import bcrypt
import json
health_tips=json.load(open(os.getcwd()+'/health_tips.json'))


app = Flask(__name__)
app.secret_key='your_secret_key'

upload_folder = os.path.join('static', 'uploads')
 
app.config['UPLOAD'] = upload_folder

PROJECT_ROOT = os.path.dirname(os.path.realpath(__file__))
DATABASE = os.path.join(PROJECT_ROOT, 'instance', 'database.db')
app.config['SQLALCHEMY_DATABASE_URI']='sqlite:///'+DATABASE
db = SQLAlchemy(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))

    def __init__(self,email,password,name):
        self.name = name
        self.email = email
        self.password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    
    def check_password(self,password):
        return bcrypt.checkpw(password.encode('utf-8'),self.password.encode('utf-8'))

with app.app_context():
    db.create_all()

model = tf.keras.models.load_model(os.getcwd()+'\\my_model.keras')

label_mapping = {
    0: 'Melanocytic nevi (nv)',
    1: 'Melanoma (mel)',
    2: 'Benign keratosis-like lesions (bkl)',
    3: 'Basal cell carcinoma (bcc)',
    4: 'Actinic keratoses (akiec)',
    5: 'Vascular lesions (vasc)',
    6: 'Dermatofibroma (df)'
}

def predict_skin_disease(image_path):
    print(image_path)
    img = cv2.imread(image_path)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    img = cv2.resize(img, (32, 32)) 
    img = img / 255
    pred = model.predict(np.array([img]))[0]
    predicted_class_index = np.argmax(pred)
    print('index:',predicted_class_index,' ',image_path)
    predicted_class_name = label_mapping[predicted_class_index]
    return predicted_class_name


@app.route('/',methods=["GET","POST"])
def index():
    if session.get("email"):
        user = User.query.filter_by(email=session['email']).first()
        return render_template('index.html',user=user)

    return render_template('index.html')

@app.route('/predict',methods=["GET","POST"])
def predict():
    if session.get("email"):
        user = User.query.filter_by(email=session['email']).first()
        if request.method=='POST':
            file=request.files["skin_photo"]
            filename = secure_filename(file.filename)
            upload_dir=os.path.join(app.config['UPLOAD'], filename)
            file.save(upload_dir)
            result=predict_skin_disease(upload_dir)
            session["disease"]=result            
            return render_template('predict.html',img=upload_dir,disease=result,user=user)

        return render_template('predict.html',user=user)
    flash('Please Login First')
    return render_template('login.html')

    

@app.route('/register',methods=["GET","POST"])
def register():
    if request.method=="POST":
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        new_user = User(name=name,email=email,password=password)
        db.session.add(new_user)
        db.session.commit()
        return redirect('/login')
       
    
    return render_template("register.html")

@app.route('/login',methods=["GET","POST"])
def login():
    if request.method=="POST":
        email = request.form['email']
        password = request.form['password']

        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            session['email'] = user.email
            return redirect('/')
        else:
            return render_template('login.html',error='Invalid user')
    
    return render_template("login.html")


@app.route('/logout')
def logout():
    session.pop('email',None)
    session.pop('disease',None)
    return redirect("/")

@app.route('/Health_Tips')
def Health_Tips():
    if session.get("email") and session.get("disease"):
       user = User.query.filter_by(email=session['email']).first()
       disease=session["disease"]
       tips=health_tips[disease]       
       return render_template("Health_Tips.html",disease=disease,user=user,health_tips_disease=tips,len=len(tips))
    else:
       return redirect("/predict")

if __name__== "__main__":
    app.run(debug=True)

