from flask import Flask, jsonify, request
import random

app = Flask(__name__)

@app.route("/api/users")
def users():
    return jsonify({"users": ["michael", "alex"]})

@app.route("/api/products")
def products():
    return jsonify({"products": ["laptop", "phone"]})

@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json()

    if not data:
        return jsonify({"error": "JSON body required"}), 400

    username = data.get("username")
    password = data.get("password")

    if username == "admin" and password == "password123":
        return jsonify({"message": "Login successful"}), 200

    return jsonify({"error": "Invalid credentials"}), 401

@app.route("/api/admin")
def admin():
    return jsonify({"message": "Admin area"})

@app.route("/api/health")
def health():
    return jsonify({"status": "OK"})

@app.errorhandler(404)
def not_found(error):
    #error_type = random.choice(["text", "json", "html"])

    #if error_type == "text":
     #   return "ERROR: Resource not found. Request ID: 12345", 404

#    if error_type == "json":
 #       return jsonify({
  #          "error": "The requested endpoint does not exist",
   #         "message": "Resource not found"
    #    }), 404

   # return """
   # <html>
    #    <body>
     #       <h1>404 Not Found</h1>
      #      <p>The requested resource could not be found.</p>
       # </body>
    #</html>
    #""", 404
    return "ERROR: Resource not found.", 404

@app.route("/api/soft404")
def soft404():
   # return "ERROR: Resource not found. Request ID: 67890", 200
     return "The page you requested could not be found.", 200

@app.route("/api/info")
def info():
     return "Welcome to our For You Page in Advertisement", 200

@app.route("/api/similar404")
def similar404():
    return "ERROR: Resource not found. Request ID: 12346", 200

@app.route("/api/json404")
def json404():
    return jsonify({
        "message": "Resource not found",
        "error": "The requested endpoint does not exist"
    }), 404

@app.route("/api/versionmessage")
def versionmessage():
    return """
    <html>
        <body>
            <p>The requested endpoint does not exist in API version 1.</p>
        </body>
    </html>
    """, 200
@app.route("/api/dbmessage")
def dbmessage():
    return jsonify({
        "message": "The requested resource was not found in the database",
        "status": "success"
    }), 200
app.run(host="127.0.0.1", port=5000)
