{ pkgs }: {
  deps = [
    pkgs.python311
    pkgs.python311Packages.pip
    # βιβλιοθήκες συστήματος για τα pip wheels (PyMuPDF/reportlab)
    pkgs.stdenv.cc.cc.lib
    pkgs.freetype
    pkgs.zlib
  ];
  env = {
    LD_LIBRARY_PATH = pkgs.lib.makeLibraryPath [
      pkgs.stdenv.cc.cc.lib
      pkgs.freetype
      pkgs.zlib
    ];
  };
}
