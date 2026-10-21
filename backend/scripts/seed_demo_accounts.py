"""Create development demo accounts. Run from backend with python -m scripts.seed_demo_accounts."""
from app.api import auth


def main():
    for index, tool in enumerate(('diabetes', 'retinopathy', 'wound', 'diet'), 1):
        email = f'{tool}@diabeticcare.com'
        if auth.find(email):
            print(f'{tool}: account already exists; unchanged')
            continue
        user = {
            'email': email, 'name': f'{tool.title()} Demo', 'username': f'demo_{tool}',
            'phone': f'077000000{index}', 'is_diabetic': True, 'role': 'patient',
            'dashboard': f'/dashboard/{tool}',
            'password_hash': auth.bcrypt.hashpw(b'2026!', auth.bcrypt.gensalt()).decode(),
        }
        auth.save(user)
        print(f'{tool}: development demo account created')


if __name__ == '__main__':
    main()
