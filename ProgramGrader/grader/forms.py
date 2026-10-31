from decimal import Decimal

from django import forms
from django.core.validators import RegexValidator

from .models import Criterion, Exam, Folder, Question, TestCase
from .scoring import criterion_cap, fmt


class FolderForm(forms.ModelForm):
    class Meta:
        model = Folder
        fields = ['name']
        widgets = {'name': forms.TextInput(attrs={'placeholder': '例如 113上 程式設計'})}


class ExamForm(forms.ModelForm):
    class Meta:
        model = Exam
        fields = ['folder', 'name']  # folder 隱藏但要在表單內，同資料夾不可重名的檢查才會生效
        widgets = {'folder': forms.HiddenInput(),
                   'name': forms.TextInput(attrs={'placeholder': '例如 A 或 期中考'})}


class QuestionForm(forms.ModelForm):
    # 題號需和檔名的題號一致，importer 只接受英數字
    code = forms.CharField(label='題號', max_length=50,
                           validators=[RegexValidator(r'^[A-Za-z0-9]+$', '題號只能用英文字母與數字')],
                           widget=forms.TextInput(attrs={'placeholder': '例如 A01'}),
                           help_text='需與檔名 學號_A01.py 的題號相同')
    points = forms.DecimalField(label='配分', min_value=Decimal('0.01'), max_digits=6, decimal_places=2,
                                widget=forms.NumberInput(attrs={'placeholder': '例如 20', 'step': 'any'}),
                                help_text='這題總分')
    time_limit = forms.IntegerField(label='時間限制（秒）', min_value=1, initial=5,
                                    help_text='每組測資最多執行幾秒，預設 5')

    class Meta:
        model = Question
        fields = ['code', 'points', 'time_limit', 'order']

    def clean_code(self):
        return self.cleaned_data['code'].upper()


class CriterionForm(forms.ModelForm):
    weight = forms.DecimalField(label='比例 (%)', min_value=0, max_value=100, max_digits=5, decimal_places=2,
                                widget=forms.NumberInput(attrs={'step': 'any'}),
                                help_text='百分比，所有項目加總需為 100')

    class Meta:
        model = Criterion
        fields = ['name', 'weight', 'description', 'order']
        widgets = {'description': forms.Textarea(attrs={'rows': 2, 'placeholder': '評分時要看什麼'})}


class CriterionFormSetBase(forms.BaseInlineFormSet):
    def clean(self):
        super().clean()
        if any(self.errors):
            return
        total = sum((f.cleaned_data['weight'] for f in self.forms if f.cleaned_data.get('weight') is not None),
                    Decimal('0'))
        if total != 100:
            raise forms.ValidationError(f'比例加總需為 100%，目前為 {fmt(total)}%')


QuestionFormSet = forms.inlineformset_factory(Exam, Question, form=QuestionForm, extra=1, can_delete=False)
CriterionFormSet = forms.inlineformset_factory(Exam, Criterion, form=CriterionForm, formset=CriterionFormSetBase,
                                               extra=0, can_delete=False)


class CaseForm(forms.ModelForm):
    class Meta:
        model = TestCase
        fields = ['input_text', 'expected_output', 'order']
        widgets = {
            'input_text': forms.Textarea(attrs={'rows': 4, 'placeholder': '就像在終端機輸入的內容，每行一個值'}),
            'expected_output': forms.Textarea(attrs={
                'rows': 4, 'placeholder': '程式應印出的內容；不用包含 input() 的提示文字，行尾空白會被忽略'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for key in ('input_text', 'expected_output'):
            self.fields[key].strip = False  # 測資的前後空白也是內容

    def clean(self):
        data = super().clean()
        for key in ('input_text', 'expected_output'):
            if key in data:  # 瀏覽器 textarea 送出的是 CRLF
                data[key] = data[key].replace('\r\n', '\n')
        return data


CaseFormSet = forms.inlineformset_factory(Question, TestCase, form=CaseForm, extra=1, can_delete=True)


class GradeForm(forms.Form):
    comment = forms.CharField(label='評語（選填）', required=False, widget=forms.Textarea(attrs={'rows': 3}))

    def __init__(self, *args, criteria, points, **kwargs):
        super().__init__(*args, **kwargs)
        self.criteria = list(criteria)
        for c in self.criteria:
            cap = criterion_cap(points, c.weight)
            self.fields[f'c{c.id}'] = forms.DecimalField(
                label=f'{c.name}（上限 {fmt(cap)}）', help_text=c.description,
                min_value=0, max_value=cap, max_digits=6, decimal_places=1,
                error_messages={'max_value': f'不可超過上限 {fmt(cap)}'},
                widget=forms.NumberInput(attrs={'step': '0.1'}))
        if self.criteria:
            self.fields[f'c{self.criteria[0].id}'].widget.attrs['autofocus'] = True
        self.fields['comment'] = self.fields.pop('comment')  # 評語放最後

    def scores(self):
        return {c: self.cleaned_data[f'c{c.id}'] for c in self.criteria}
