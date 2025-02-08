import random
import string
from flask import Flask, render_template, session, redirect, url_for, request
from flask_socketio import SocketIO, send, join_room, leave_room

app = Flask(__name__)
app.config['SECRET_KEY'] = '#gupta098'
socketio = SocketIO(app)

DEFAULT_ROOM_CODE = "CN"
rooms = {
    DEFAULT_ROOM_CODE: {
        "members": 0, 
        "messages": [
            {"name": "System", "message": "Welcome to the default chat room!"},
            {"name": "System", "message": "Feel free to start chatting."}
        ]
    }
}

def generate_unique_code(length):
    """Generate a unique room code."""
    while True:
        code = ''.join(random.choices(string.ascii_uppercase, k=length))
        if code not in rooms:
            break
    return code

@app.route("/", methods=["POST", "GET"])
def home():
    """Home page for creating or joining rooms."""
    session.clear()
    
    if request.method == "POST":
        name = request.form.get("name")
        code = request.form.get("code")
        join = request.form.get("join", False)
        create = request.form.get("create", False)
        
        if not name:
            return render_template("home.html", error="Please enter a name.", code=code, name=name)
        
        if join != False and not code:
            return render_template("home.html", error="Please enter a room code.", code=code, name=name)
        
        # Determine room
        room = code
        if create != False:
            room = generate_unique_code(4)
            rooms[room] = {"members": 0, "messages": []}
        elif code not in rooms:
            return render_template("home.html", error="Room does not exist.", code=code, name=name)
        
        session["room"] = room
        session["name"] = name
        return redirect(url_for("room_page", room_code=room))
    
    return render_template("home.html")

@app.route("/room/<room_code>")
def room_page(room_code):
    """Room page for chat interaction with dynamic URL."""
    # If user tries to access room directly without session, ask for name
    if session.get("name") is None:
        return redirect(url_for("join_specific_room", room_code=room_code))
    
    # Verify room exists
    if room_code not in rooms:
        return redirect(url_for("home"))
    
    session["room"] = room_code
    return render_template("room.html", code=room_code, messages=rooms[room_code]["messages"])

@app.route("/join/<room_code>", methods=["GET", "POST"])
def join_specific_room(room_code):
    """Handle joining a specific room from its URL."""
    if request.method == "POST":
        name = request.form.get("name")
        
        if not name:
            return render_template("join_room.html", error="Please enter a name.", room_code=room_code)
        
        if room_code not in rooms:
            return render_template("join_room.html", error="Room does not exist.", room_code=room_code)
        
        session["name"] = name
        session["room"] = room_code
        return redirect(url_for("room_page", room_code=room_code))
    
    return render_template("join_room.html", room_code=room_code)

# Keep existing socket event handlers
@socketio.on("message")
def message(data):
    """Handle incoming messages."""
    room = session.get("room")
    if room not in rooms:
        return 
    content = {
        "name": session.get("name"),
        "message": data["data"]
    }
    send(content, to=room)
    rooms[room]["messages"].append(content)
    print(f"{session.get('name')} said: {data['data']}")

@socketio.on("connect")
def connect(auth):
    """Handle user connection to a room."""
    room = session.get("room")
    name = session.get("name")
    
    if not room or not name:
        return
    if room not in rooms:
        leave_room(room)
        return
    
    join_room(room)
    send({"name": name, "message": "has entered the room"}, to=room)
    rooms[room]["members"] += 1
    socketio.emit('member_count', {'count': rooms[room]["members"]}, to=room)
    print(f"{name} joined room {room}")

@socketio.on("disconnect")
def disconnect():
    """Handle user disconnection from a room."""
    room = session.get("room")
    name = session.get("name")
    
    leave_room(room)
    
    if room in rooms:
        rooms[room]["members"] -= 1
        if rooms[room]["members"] <= 0:
            del rooms[room]
    
    socketio.emit('member_count', {'count': rooms[room]["members"]}, to=room)
    send({"name": name, "message": "has left the room"}, to=room)
    print(f"{name} has left the room {room}")

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)