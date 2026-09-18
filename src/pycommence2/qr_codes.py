import qrcode

IP = 'http://192.168.1.80:8000'


def open_in_commence_link(category, pk_value):
    link = f'{IP}/show/{category}/{pk_value}'
    return link


def test_link():
    link = f'{IP}/test'
    return link


def make_qr(data):
    qr = qrcode.make(data)
    img = qr.get_image()
    img.save('qr_test.png')


if __name__ == '__main__':
    link = open_in_commence_link('Contact', 'Bezos.Jeff')
    link = test_link()
    make_qr(link)
