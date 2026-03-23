from django import forms


class BaristaScanForm(forms.Form):
    qr_code_uuid = forms.UUIDField(
        label='UUID из QR',
        widget=forms.TextInput(
            attrs={
                'placeholder': 'Вставьте UUID из QR-кода',
                'autocomplete': 'off',
            }
        ),
    )
