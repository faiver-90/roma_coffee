from django import forms
from django.contrib.auth import authenticate, password_validation
from django.core.exceptions import ValidationError

from .models import PasswordResetCode, User
from .utils import normalize_phone, phone_lookup_values


class PhoneInputMixin:
    phone_widget = forms.TextInput(
        attrs={
            'autocomplete': 'tel',
            'placeholder': '+7 999 999 99 99',
            'inputmode': 'numeric',
            'maxlength': '16',
            'data-phone-mask': 'true',
        }
    )


class RegisterForm(PhoneInputMixin, forms.ModelForm):
    password1 = forms.CharField(
        label='Пароль',
        strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
    )
    password2 = forms.CharField(
        label='Повторите пароль',
        strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
    )

    class Meta:
        model = User
        fields = ('phone',)
        widgets = {'phone': PhoneInputMixin.phone_widget}
        labels = {'phone': 'Телефон'}

    def clean_phone(self):
        phone = normalize_phone(self.cleaned_data['phone'])
        if User.objects.filter(phone__in=phone_lookup_values(phone)).exists():
            raise ValidationError('Пользователь с таким телефоном уже существует.')
        return phone

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')

        if password1 and password2 and password1 != password2:
            self.add_error('password2', 'Пароли не совпадают.')

        if password1:
            try:
                password_validation.validate_password(password1)
            except ValidationError as exc:
                self.add_error('password1', exc)

        return cleaned_data

    def save(self, commit: bool = True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        if commit:
            user.save()
        return user


class LoginForm(PhoneInputMixin, forms.Form):
    phone = forms.CharField(label='Телефон', widget=PhoneInputMixin.phone_widget)
    password = forms.CharField(
        label='Пароль',
        strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'current-password'}),
    )

    error_messages = {
        'invalid_login': 'Неверный телефон или пароль.',
        'inactive': 'Аккаунт отключен.',
    }

    def __init__(self, request=None, *args, **kwargs):
        self.request = request
        self.user = None
        super().__init__(*args, **kwargs)

    def clean_phone(self):
        return normalize_phone(self.cleaned_data['phone'])

    def clean(self):
        cleaned_data = super().clean()
        phone = cleaned_data.get('phone')
        password = cleaned_data.get('password')
        if phone and password:
            self.user = authenticate(self.request, username=phone, password=password)
            if self.user is None:
                raise ValidationError(self.error_messages['invalid_login'])
            if not self.user.is_active:
                raise ValidationError(self.error_messages['inactive'])
        return cleaned_data

    def get_user(self):
        return self.user


class PasswordResetRequestForm(PhoneInputMixin, forms.Form):
    phone = forms.CharField(label='Телефон', widget=PhoneInputMixin.phone_widget)

    def clean_phone(self):
        return normalize_phone(self.cleaned_data['phone'])


class PasswordResetConfirmForm(PhoneInputMixin, forms.Form):
    phone = forms.CharField(label='Телефон', widget=PhoneInputMixin.phone_widget)
    code = forms.CharField(
        label='Код',
        max_length=6,
        min_length=6,
        widget=forms.TextInput(attrs={'autocomplete': 'one-time-code', 'placeholder': '123456'}),
    )
    password1 = forms.CharField(
        label='Новый пароль',
        strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
    )
    password2 = forms.CharField(
        label='Повторите пароль',
        strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
    )

    def clean_phone(self):
        return normalize_phone(self.cleaned_data['phone'])

    def clean(self):
        cleaned_data = super().clean()
        phone = cleaned_data.get('phone')
        code = cleaned_data.get('code')
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')
        user = None

        if password1 and password2 and password1 != password2:
            self.add_error('password2', 'Пароли не совпадают.')

        if phone:
            user = User.objects.filter(phone__in=phone_lookup_values(phone)).first()
            if user is None:
                self.add_error('phone', 'Пользователь не найден.')

        if user and code:
            reset_record = PasswordResetCode.objects.filter(user=user, used_at__isnull=True).first()
            if reset_record is None or not reset_record.is_active() or not reset_record.matches(code):
                self.add_error('code', 'Неверный или просроченный код.')

        if password1:
            try:
                password_validation.validate_password(password1, user=user)
            except ValidationError as exc:
                self.add_error('password1', exc)

        return cleaned_data
