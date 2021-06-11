from flask import Flask, render_template, request, session,redirect,url_for, flash
from flask_sqlalchemy import SQLAlchemy
import speech_recognition as sr
import _thread
import pywhatkit as kit
from time import ctime
import webbrowser
import playsound
import os
import random
from gtts import gTTS
import time
import sounddevice as sd
import wavio as wv
from scipy.io.wavfile import write
import wave
import numpy as np
import datetime
from win10toast import ToastNotifier 


r = sr.Recognizer()

# save audio
freq = 44100  # 100-800 range normally
duration = 3
stop_threads = False

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = 'sqlite:///user.db'
db = SQLAlchemy(app)
app.secret_key='abc'

#model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    Username = db.Column(db.String(80), nullable=False)
    Email = db.Column(db.String(120), nullable=False)
    Password  = db.Column(db.String(120), nullable=False)
    Gender = db.Column(db.String(120), nullable=False)

    def __repr__(self):
        return '<User %r>' % self.Username

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    Email = db.Column(db.String(120), nullable=False)
    Reminder = db.Column(db.String(280), nullable=False)
    Time = db.Column(db.String(280), nullable=False)

def User_Event(email):
    task = Event.query.filter(Event.Email == email)
    while True:
        for e in task:
            if (e.Time == datetime.datetime.now().strftime("%H:%M")):
                druid_speak("It's time for "+e.Reminder)
                n = ToastNotifier() 
                n.show_toast("DRUID REMINDER", "It's time for " + e.Reminder ,duration = 50000) 
                time.sleep(60)
        global stop_threads 
        if stop_threads: 
            break
#start
@app.route("/")
def a():
    return render_template("login.html") 

@app.route('/login',methods = ['POST', 'GET'])
def login():
    if request.method == 'GET':
        return render_template("login.html")    
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['pass']
        user = User.query.all()
        for u in user:
            if u.Email == email and u.Password == password:
                session.pop('username',None)
                session.pop('email',None)
                session['username'] = u.Username
                session['email'] = u.Email
                try:
                    global stop_threads
                    stop_threads = False
                    _thread.start_new_thread(User_Event,(email,))
                except:
                    print('ERROR while starting thread:(')
                return redirect(url_for("home"))
        error_msg = "Invalid Email or Password" 
        return render_template('login.html',error_msg=error_msg)   
    

@app.route('/register',methods = ['GET','POST'])
def register():
    if request.method == 'GET':
        return render_template("register.html")
    if request.method == 'POST':
        try:
            user = User.query.filter_by(Email = request.form['email']).first()
            if user is None:
            # u = User(Username= name,Password=password,Gender=gender,Email=email)
                u = User()
                u.Username = request.form['username']
                u.Password = request.form['pass']
                u.Gender= request.form['gender']
                u.Email = request.form['email']
                db.session.add(u)
                db.session.commit()
                return redirect(url_for("login"))
            else:
                error_msg = "Email id is already taken." 
                return render_template('register.html',error_msg=error_msg)
        except:
            print("error while uploading")


@app.route('/logout',methods=['GET','POST'])
def logout():
    session.pop('username',None)
    session.pop('email',None)
    global stop_threads
    stop_threads = True
    return render_template("login.html",logout='logout')


@app.route('/home',methods = ['POST', 'GET'])
def home():
    if 'username' in session:
        if session['username']:
            email = session['email']
            user = User.query.filter_by(Email = email).first()
            return render_template("index.html",user=user)
    return redirect(url_for("login"))


@app.route('/profile',methods=['GET','POST'])
def profile():
    if 'email' in session:
        email = session['email']
        if request.method == 'POST':
            user = User.query.filter_by(Email = email).first()
            user.Username = request.form['username']
            user.Password = request.form['pass']
            user.Gender= request.form['gender']
            user.Email = request.form['email']
            db.session.commit()
            msg='Profile Updated Sucsessfully'
            return render_template("profile.html",user=user,msg=msg)
        else:
            user = User.query.filter_by(Email = email).first()
            return render_template("profile.html",user=user)
    return redirect(url_for("login"))


@app.route('/delete_account',methods=['GET','POST'])
def delete():
    email = session['email']
    user = User.query.filter_by(Email = email).delete()
    Event.query.filter_by(Email = email).delete()
    db.session.commit()
    return redirect(url_for("login"))

@app.route('/events',methods=['GET','POST'])
def events():
    if 'email' in session:
        e = Event.query.filter_by(Email = session['email'])
        if e.count() == 0:
            msg = 'No Reminder Available'
            return render_template("events.html",msg = msg)    
        return render_template("events.html",event = e)
    else:
        return redirect(url_for("login"))

@app.route('/delete_event/<id>')
def delete_event(id):
    Event.query.filter_by(id = id).delete()
    db.session.commit()
    return redirect(url_for('events'))
    

@app.route('/speak/<audio_string>')
def druid_speak(audio_string):
    tts = gTTS(text=audio_string, lang='en')
    ran = random.randint(1, 10000000000)
    audio_file = 'audio-' + str(ran) + '.mp3'
    tts.save(audio_file)
    playsound.playsound(audio_file)
    os.remove(audio_file)
    return 'Done'


def respond(voice_data):
    if 'what is your name' in str(voice_data).lower():
        return 'My name is Druid'

    elif 'what time is it' in str(voice_data).lower():
        return ctime()

    elif "save my audio" in str(voice_data).lower():  # working
        name = voice_data.replace('save my audio ', '')
        druid_speak("please say who am i")
        print('lisening for 3 seconds')
        recording = sd.rec(int(duration * freq), samplerate=freq, channels=2)
        sd.wait()
        write(name + '.wav', freq, recording.astype(np.int16))
        print('your voice recorded succesfullly.')

    elif 'what is my name' in str(voice_data).lower():  # working
        if 'email' in session:
            user = User.query.filter_by(Email = session['email']).first()
            return 'your name is ' + user.Username
        # working for compare two audio file
        # print('lisening for 3 seconds')
        # recording = sd.rec(int(duration * freq), samplerate=freq, channels=2)
        # sd.wait()
        # write('temp.wav', freq, recording.astype(np.int16))
        # allfiles = os.listdir('.')
        # w_two = wave.open('temp.wav')
        # for audio in allfiles:
        #     if audio.endswith('.wav') and audio!= 'temp.wav':
        #         w_one = wave.open(audio)
        #         if w_one.readframes(w_one.getnframes()) == w_two.readframes(w_two.getnframes()):
        #             print(audio)
        #             break
        #         else:
        #             print('not a match')
        #         w_one.close()
        # w_two.close()
        # os.remove('temp.wav')

    elif ('start' in str(voice_data).lower() or ('open' in str(voice_data).lower())):
        if 'start' in voice_data:
            app = voice_data.replace('start ', '')
        else:
            app = voice_data.replace('open ', '')
        os.system(app)
        return 'Starting ' + app

    elif 'close' in str(voice_data).lower():
        app = voice_data.replace('close ', '')
        os.system('TASKKILL /F /IM ' + app + '.exe')
        return 'Closing ' + app

    elif voice_data.find('play') != -1:
        name = voice_data.replace('play ', '')
        kit.playonyt(name)
        return 'Here is what i play for ' + name + ' on youtube'

    elif voice_data.find('search location') != -1:
        location = voice_data.replace('search location ', '')
        url = 'https://google.com/maps/place/' + location
        webbrowser.get().open(url)
        return 'Here is the location of ' + location

    elif voice_data.find('search Wikipedia') != -1:
        name = voice_data.replace('search Wikipedia ', '')
        url = 'https://en.wikipedia.org/wiki/' + name
        webbrowser.get().open(url)
        return 'Here is what i found for ' + name + ' on wikipedia'

    elif voice_data.find('search') != -1:
        name = voice_data.replace('search ', '')
        url = 'https://google.com/search?q=' + name
        webbrowser.get().open(url)
        return 'Here is what i found for ' + name

    #set reminder on time for sentence
    elif voice_data.find('set reminder') != -1:
        start = voice_data.find('on')
        end = voice_data.find('for')
        time = voice_data[start+3:end-1]
        time_arr = time.split()
        if len(time_arr)==3:
            str1 = time_arr[0] + ':' + time_arr[1]
            time_arr.pop(0)
            time_arr[0] = str1
        if len(time_arr[0]) <=2 :
            time_arr[0] += ':00' 
        if time_arr[1]=='a.m.':
            time_arr[1]='AM'
        else:
            time_arr[1]='PM' 
        if time_arr[0][2] !=':':
            time_arr[0] = time_arr[0][:2] + ':' + time_arr[0][3:]
        try:
            time = time_arr[0] + ' ' + time_arr[1]
            in_time = datetime.datetime.strptime(time, "%I:%M %p")
            out_time = datetime.datetime.strftime(in_time, "%H:%M")
            sentence = voice_data[end+4:]
        except:
            return "please speak again"
        e = Event()
        e.Email = session['email']
        e.Reminder = sentence
        e.Time = out_time
        db.session.add(e)
        db.session.commit()
        return 'Reminder Saved'

    elif 'exit' in str(voice_data).lower():
        druid_speak('Have a good day! bye.')
        exit()

    else:
        return 'sorry my service is down for this word'


@app.route("/record/")
def record_audio():
    voice='voice'
    Druid='Druid'
    with sr.Microphone() as source:
        voice_data = ''
        audio = r.listen(source,phrase_time_limit=5)
        try:
            voice_data = r.recognize_google(audio)
        except sr.UnknownValueError:
            druid_speak("sorry i didn't get that")
        except sr.RequestError:
            druid_speak("sorry my service is down now")
        Druid_ans = respond(voice_data)
        # druid_speak(Druid_ans)
        
        return ({ voice:voice_data,Druid:Druid_ans })


if __name__ == '__main__':
    app.run(debug=True)
