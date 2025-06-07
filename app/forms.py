from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, TextAreaField, DecimalField, SubmitField, MultipleFileField, URLField
from wtforms.validators import DataRequired, NumberRange, Optional, URL

class QuestionForm(FlaskForm):
    name = StringField('Question Name', validators=[DataRequired()])
    content = TextAreaField('LaTeX Content', validators=[DataRequired()])
    answer = TextAreaField('Answer', validators=[DataRequired()])
    rating = DecimalField('Difficulty Rating (1.0-10.0)', 
                          validators=[DataRequired(), 
                                     NumberRange(min=1.0, max=10.0, 
                                                message='Rating must be between 1.0 and 10.0')],
                          places=1)
    submit = SubmitField('Add Question')

class AttachmentForm(FlaskForm):
    attachment_file = MultipleFileField('Attach Files', validators=[
        Optional(),
        FileAllowed(['pdf', 'png', 'jpg', 'jpeg', 'webm', 'mp4', 'docx', 'xlsx', 'pptx'], 
                   'Only specific file types are allowed!')
    ])
    attachment_url = URLField('Add URL', validators=[Optional(), URL()])
    submit = SubmitField('Add Attachment') 