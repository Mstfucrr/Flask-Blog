from flask import Flask, render_template, flash, redirect, url_for, session, logging, request
from flask_mysqldb import MySQL
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from passlib.hash import sha256_crypt
from functools import wraps


#kullanıcı giriş Decorator'ı

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "logged_in" in session:
            return f(*args, **kwargs)
        else:
            flash("Bu sayfayı görüntülemek için lütfen giriş yapın","danger")
            return redirect(url_for("login"))
    return decorated_function

# kullanıcı kayıt formu
app = Flask(__name__)
app.secret_key = 'super secret key'
app.config["MYSQL_HOST"] = "localhost"
app.config["MYSQL_USER"] = "root"
app.config["MYSQL_PASSWORD"] = ""
app.config["MYSQL_DB"] = "blog"
app.config["MYSQL_CURSORCLASS"] = "DictCursor"


mysql = MySQL(app)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/about")
def about():
    return render_template("about.html")

# dashboard
@app.route("/dashboard")
@login_required
def dashboard():
    cursor = mysql.connection.cursor()

    sorgu = "Select * From articles where author = '{}'"
    result = cursor.execute(sorgu.format(session["username"]))

    if result > 0:
        dash_articles = cursor.fetchall()
        return render_template("dashboard.html",dash_articles = dash_articles)
    else:
        return render_template("dashboard.html")


# Kayıt
class RegisterForm(Form):
    name = StringField("İsim Soyisim", validators=[
                       validators.length(min=4, max=25)])
    username = StringField("Kullanıcı Adı", validators=[
                           validators.length(min=5, max=35)])
    email = StringField("Email Adresi", validators=[validators.email(
        message="Lütfen geçerli bir email adresi giriniz")])
    password = PasswordField("Parola: ", validators=[
        validators.DataRequired(message="Lütfen bir parola belirleyin"),
        validators.EqualTo(fieldname="confirm",
                           message="Parolanız Uyuşmuyor...")
    ])
    confirm = PasswordField("Parola Doğrula")

@app.route("/register", methods=["GET", "POST"])
def register():
    form = RegisterForm(request.form)

    if request.method == "POST" and form.validate():
        # formdan alınan verileri değişkenlere verme
        name = form.name.data
        username = form.username.data
        email = form.email.data
        password = sha256_crypt.encrypt(form.password.data)

        cursor = mysql.connection.cursor()

        # değişkenleri mysql veritabanına kaydetme
        cursor.execute("Insert into users Values('','%s','%s','%s','%s')" % (
            name, email, username, password))

        # ekleme,silme ve verileri güncellemek için mutlaka 'commit' gerekli
        mysql.connection.commit()
        cursor.close()  # veritabanı bağlantı kesilme

        flash("Başarıyla Kayıt Oldunuz", "success")

        return redirect(url_for("login"))
    else:
        return render_template("register.html", form=form)


# Giriş yap
class LoginForm(Form):
    username = StringField("Kullanıcı Adı")
    password = PasswordField("Şifre")

@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm(request.form)

    if request.method == "POST":
        # formdan alınan verileri değişkenlere verme
        username = form.username.data
        password_entered = form.password.data
        cursor = mysql.connection.cursor()
        sorgu = "Select * from users where username = '{}'"
        result = cursor.execute(sorgu.format(username))

        if result > 0:
            data = cursor.fetchone()
            real_password = data["password"]
            if sha256_crypt.verify(password_entered, real_password):
                flash("Başarıyla giriş yaptınız", "success")
                session["logged_in"] = True
                session["username"] = username

                return redirect(url_for("index"))
            else:
                flash("Parolanızı yanlış girdiniz", "danger")
                return redirect(url_for("login"))
        else:
            flash("Böyle bir kullanıcı adı bulunmuyor", "danger")
            return redirect(url_for("login"))

        mysql.connection.commit()
        cursor.close()
    return render_template("login.html", form=form)



# logout işlemi
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


# makale form

class ArticleForm(Form):
    title = StringField("Makale Başlığı",validators=[validators.Length(min = 5,max=100)])
    content = TextAreaField("Makale İçeriği",validators=[validators.Length(min=10)])

#makale ekleme 
@app.route("/addarticle",methods=["Get","POST"])
def addarticle():
    form = ArticleForm(request.form)
    if request.method == "POST" and form.validate():
        title = form.title.data
        content = form.content.data

        cursor = mysql.connection.cursor()
        sorgu = "Insert into articles(title,author,content) VALUES(%s,%s,%s)"
        cursor.execute(sorgu,(title,session["username"],content))
        mysql.connection.commit()
        cursor.close()
        flash("Makale Başarıyla Eklendi","success")
        return redirect(url_for("dashboard"))
    
    return render_template("addarticle.html",form = form)


# Makaleler'i görüntüleme
@app.route("/articles")
def articles():
    cursor = mysql.connection.cursor()
    
    sorgu = "Select * From articles"
    result = cursor.execute(sorgu)

    if result > 0:
        articles = cursor.fetchall()
        return render_template("articles.html",articles=articles)
    else:
        return render_template("articles.html")


class CommentForm(Form):
    comment = TextAreaField("Yorum yap",validators=[validators.Length(min=10)])

# makale detay sayfası
@app.route("/article/<string:id>",methods=["Get","POST"])
def article(id):
    form = CommentForm(request.form)
    cursor = mysql.connection.cursor()
    sorgu = "Select * From articles where id = %s"
    result = cursor.execute(sorgu,(id,))

    if result > 0:
        article = cursor.fetchone()
    else:
        return render_template("article.html",form=form)  
    
    sorgu3 = "Select * From comments where id = %s"
    cursor.execute(sorgu3,(id,))
    comments = cursor.fetchall()
    comment = form.comment.data
    if request.method=="POST" and form.validate():
        sorgu2 = "Insert into comments(id,username,comment_content) VALUES(%s,%s,%s)"
        cursor.execute(sorgu2,(id,session["username"],comment))
        mysql.connection.commit()
        cursor.close()
        flash("Yorumunuz başarıyla eklendi","success")
        return redirect(url_for("article",id=id))


    return render_template("article.html",article= article,comments = comments,form = form)



# Makale güncelleme
@app.route("/edit/<string:id>",methods = ["GET","POST"])
@login_required
def edit(id):
    if request.method == "GET":
        cursor = mysql.connection.cursor()
        sorgu = "Select * from articles where id = %s and author = %s"
        result = cursor.execute(sorgu,(id,session["username"]))
        if result == 0:
            flash("Böyle bir makale yok veya bu işleme yetkiniz yok","danger")
            return redirect(url_for("index"))
        else:
            article = cursor.fetchone()
            form = ArticleForm()
            form.title.data = article["title"]
            form.content.data = article["content"]
            return render_template("edit.html",form = form)
    #post Request
    form = ArticleForm(request.form)
    newTitle = form.title.data
    newContent = form.content.data
    sorgu2 = "Update articles Set title = %s,content = %s where id = %s"
    cursor = mysql.connection.cursor()
    cursor.execute(sorgu2,(newTitle,newContent,id))
    mysql.connection.commit()
    flash("Makale başarıyla güncellendi","success")
    return redirect(url_for("dashboard"))

# Makale silme
@app.route("/delete/<string:id>")
@login_required
def delete(id):
    cursor = mysql.connection.cursor()
    sorgu = "Select * from articles where author = %s and id = %s"

    result = cursor.execute(sorgu,(session["username"],id))

    if result > 0:
        sorgu2 = "Delete from articles where id = %s"
        sorgu3 = "Delete from comments where id = %s"
        cursor.execute(sorgu2,(id,))
        cursor.execute(sorgu3,(id,))
        mysql.connection.commit()
        return redirect(url_for("dashboard"))
    else:
        flash("Böyle bir makale yok veya bu işleme yetkiniz yok","danger")
        return redirect(url_for("index"))



# Arama URL
@app.route("/search",methods = ["GET","POST"])
def search():
    if request.method == "GET":
        return redirect(url_for("index"))
    else:
        keyword = request.form.get("keyword")

        cursor = mysql.connection.cursor()
        sorgu = "Select * from articles where title like '%" + keyword + "%'"
        result = cursor.execute(sorgu)
        
        if result == 0:
            flash("Aranan kelimeye uygun makale bulunamadı...","warning")
            return redirect(url_for("articles"))
        else:
            articles = cursor.fetchall()
            return render_template("articles.html",articles = articles)

if __name__ == "__main__":
    app.run(debug=True)
