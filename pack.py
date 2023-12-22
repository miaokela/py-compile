import os
import time
import shutil
from distutils.core import setup
from Cython.Build import cythonize


# 确认不需要编译的文件或者文件夹
BASE_DIR = os.path.abspath(".")
BUILD_DIR = "build"
BACKUP_NAME = ".bak"

PACK_FILE_PATH = os.path.join(BASE_DIR, __file__)
BUILD_DIR_PATH = os.path.join(BASE_DIR, BUILD_DIR)
BACK_DIR_PATH = os.path.join(BASE_DIR, BACKUP_NAME)

EXCEPT_FILES = [
    PACK_FILE_PATH,  # 编译脚本 不可删除
    # 允许添加
    os.path.join(BASE_DIR, "main.py"),
]

EXCEPT_DIRS = [
    BUILD_DIR_PATH,  # 编译目录 不可删除
    BACK_DIR_PATH,  # 备份文件夹 不可删除
    # 允许添加
]


class CythonCompiler(object):
    def __init__(self, parent_path=""):
        self.start_time = time.time()
        self.cur_dir = os.path.abspath(".")
        self.parent_path = parent_path
        self.build_dir = BUILD_DIR
        self.build_temp_dir = os.path.join(self.build_dir, "temp")
        self.abs_path_root = os.path.abspath(".")
        self.excepts_file_list = EXCEPT_FILES
        self.excepts_dir_list = EXCEPT_DIRS
        self.backup_path = BACK_DIR_PATH

    def fetch_py(
        self,
        base_path=None,
        parent_path="",
        name="",
        excepts_file=(),
        excepts_dir=(),
        del_c=False,
    ):
        if base_path is None:
            base_path = self.cur_dir
        full_path = os.path.join(base_path, parent_path, name)
        for f_name in os.listdir(full_path):
            ffile = os.path.join(full_path, f_name)
            if (
                os.path.isdir(ffile)
                and not f_name.startswith(".")
                and ffile not in excepts_dir
            ):
                for f in self.fetch_py(
                    base_path,
                    os.path.join(parent_path, name),
                    f_name,
                    excepts_file,
                    excepts_dir,
                    del_c,
                ):
                    yield f
            elif os.path.isfile(ffile):
                ext = os.path.splitext(f_name)[1]
                if ext == ".c":
                    if del_c and os.stat(ffile).st_mtime > self.start_time:
                        os.remove(ffile)
                elif ffile not in excepts_file:
                    if os.path.splitext(f_name)[1] in (
                        ".py",
                        ".pyx",
                    ) and not f_name.startswith("__"):
                        yield os.path.join(parent_path, name, f_name)

    def rename(self, target_dir):
        for dir_path, _, file_names in os.walk(target_dir):
            for file_name in file_names:
                if not (
                    file_name.__contains__(".so") or file_name.__contains__(".pyd")
                ):
                    continue
                file_name_part_list = file_name.split(".")
                if len(file_name_part_list) == 3:
                    file_new_name = (
                        file_name_part_list[0] + "." + file_name_part_list[2]
                    )
                    if os.path.isfile(os.path.join(dir_path, file_new_name)):
                        os.remove(os.path.join(dir_path, file_new_name))
                    os.rename(
                        os.path.join(dir_path, file_name),
                        os.path.join(dir_path, file_new_name),
                    )

    def backup_files(self):
        backup_dir = os.path.join(self.cur_dir, ".bak")
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
        for dirpath, _, filenames in os.walk(self.cur_dir):
            if dirpath == backup_dir:
                continue

            for filename in filenames:
                if filename.endswith(".py"):
                    src_file = os.path.join(dirpath, filename)
                    dst_file = os.path.join(
                        backup_dir, os.path.relpath(src_file, self.cur_dir)
                    )
                    os.makedirs(os.path.dirname(dst_file), exist_ok=True)
                    shutil.copy2(src_file, dst_file)

    def remove_compiled_files(self):
        for dirpath, _, filenames in os.walk(self.cur_dir):
            for filename in filenames:
                if not filename.endswith(".py"):
                    continue
                so_file = os.path.join(dirpath, filename.replace(".py", ".so"))
                if os.path.exists(so_file):
                    os.remove(os.path.join(dirpath, filename))

    def compile(self, confirm_del_py=False):
        self.backup_files()  # py文件备份
        module_list = list(
            self.fetch_py(
                excepts_file=self.excepts_file_list, excepts_dir=self.excepts_dir_list
            )
        )
        try:
            setup(
                ext_modules=cythonize(
                    module_list,
                    compiler_directives=dict(
                        always_allow_keywords=True, language_level=3
                    ),
                ),
                script_args=[
                    "build_ext",
                    "-b",
                    self.cur_dir,
                    "-t",
                    self.build_temp_dir,
                ],
            )
        except Exception as e:
            print(f"\033[91m Error: {e}\033[00m")

        module_list = list(
            self.fetch_py(
                excepts_file=self.excepts_file_list,
                excepts_dir=self.excepts_dir_list,
                del_c=True,
            )
        )
        if os.path.exists(self.build_dir):
            shutil.rmtree(self.build_dir)
        self.rename(self.cur_dir)
        if confirm_del_py:
            self.remove_compiled_files()  # 删除已编译的文件
        print("Done.")


if __name__ == "__main__":
    compiler = CythonCompiler()
    compiler.compile(confirm_del_py=True)
