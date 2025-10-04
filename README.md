<h1>ApplyNest - Job/Internship postings, applications, and administrative tasks.</h1>
<hr>
<p>This is a Flask-based web application designed to streamline the job application process. It enables administrators to post and manage job listings, while applicants can register, log in, submit their resumes, and track application status. The system provides separate dashboards for users and admins, ensuring a smooth and organized recruitment workflow.</p>
<br>
<h2>Features: </h2>
<li><b>User Authentication:</b> Users can register, login, and logout. There are two types of users: admins and regular users.</ul>
<li><b>Admin Dashboard:</b> Admins can view, add, edit, and delete job postings.</li>
<li><b>User Dashboard:</b> Regular users can view job postings and apply for them.</li>
<li><b>Job Applications:</b> Admins can view job applications submitted by users.</li>
<li><b>Password Encryption:</b> Passwords are securely hashed before storing in the database.</li>
<br>
<h2>Prerequistes: </h2>
<li>Python (latest version)</li>
<li>Flask</li>
<li>SQLite3 (for the database)</li>
<br>
<h2>⚙️ Installation</h2>

<ol>
  <li>
    <strong>Clone the repository</strong>
    <pre><code>git clone https://github.com/your-username/ApplyNest-A-Flask-Application.git
cd ApplyNest-A-Flask-Application</code></pre>
  </li>
  
  <li>
    <strong>Install dependencies</strong>
    <pre><code>pip install -r requirements.txt</code></pre>
  </li>
  
  <li>
    <strong>Run the application</strong>
    <pre><code>python app.py</code></pre>
  </li>
</ol>
<br>
<h2>📁 Project Structure</h2>
<pre>
ApplyNest-Flask-Application/
│
├── static/
│   ├── css/
│      └── styles.css
├── templates/
│   ├── admin.html
│   ├── admin_dashboard.html
│   ├── index.html
│   ├── layout.html
│   ├── login.html
│   ├── register.html
│   └── user_dashboard.html
│
├── README.md
├── app.py
├── job_applications.db
└── requirements.txt
</pre>
<h2>How it looks: </h2>
<br>

![image](https://github.com/banasmita24/ApplyNest/assets/155791058/a6a63cae-fbe0-4b01-a425-a3cd1195c4b2)

![image](https://github.com/banasmita24/ApplyNest/assets/155791058/f9fcc745-c9f5-497c-90d8-8a1c997ab8e3)

![image](https://github.com/banasmita24/ApplyNest/assets/155791058/7f9502aa-8d62-495b-bbb1-e34e90ee1468)

![image](https://github.com/banasmita24/ApplyNest/assets/155791058/6a8cb7ad-632b-4995-9dc4-bc206da37897)

<br>
<h2>📝 License</h2>
<p>This project is licensed under the <a href="LICENSE">MIT License</a>.</p>
