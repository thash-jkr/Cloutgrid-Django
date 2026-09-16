from django.contrib import admin
from .models import Job, Application, Question, Answer

# Register your models here.
admin.site.register(Job)
admin.site.register(Application)
admin.site.register(Question)
admin.site.register(Answer)