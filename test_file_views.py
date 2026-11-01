import io
import unittest
from PIL import Image
from file_views import VIEWS,layout,is_picture
from picture_browser import decode_image
from project_store import validate_project

class ViewTests(unittest.TestCase):
    def test_all_layouts(self):
        self.assertEqual(len(VIEWS),7)
        for mode in VIEWS:
            for width in (100,850,1920):
                w,h,size,cols=layout(mode,width)
                self.assertGreaterEqual(cols,1);self.assertGreater(h,0);self.assertGreater(size,0)
    def test_image_types(self):
        self.assertTrue(is_picture('folder/PHOTO.JPG'))
        self.assertTrue(is_picture('a.tiff'))
        self.assertFalse(is_picture('a.html'))
        self.assertFalse(is_picture('a.heic'))
    def test_decode(self):
        data=io.BytesIO();Image.new('RGB',(400,200),'red').save(data,'PNG')
        out=decode_image(data.getvalue());self.assertEqual(out.size,(400,200));self.assertEqual(out.mode,'RGBA')
        out.thumbnail((112,112));self.assertEqual(out.size,(112,56))
    def test_bad_image(self):
        with self.assertRaises(Exception):decode_image(b'not an image')
    def test_view_project(self):
        for mode in VIEWS:
            obj={'format':'aws.manager.project','version':1,'settings':{'view_mode':mode}}
            self.assertEqual(validate_project(obj),obj)
        with self.assertRaises(ValueError):validate_project({'format':'aws.manager.project','version':1,'settings':{'view_mode':'invalid'}})

if __name__=='__main__':unittest.main()
