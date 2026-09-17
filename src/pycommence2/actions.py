from pycommence2 import CommenceSession


def show_item():
    with CommenceSession() as db:
        db.dde.show_item('Customer', 'Test')


if __name__ == '__main__':
    show_item()
