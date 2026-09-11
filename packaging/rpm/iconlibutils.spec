# Version is injected by packaging/rpm/Makefile via `zfr version`.
# RPM Version cannot contain '-'; use `zfr version -r` (hyphens → '_').
# srcversion is the unsanitized Meson/git version and names the tarball.
%{!?version:%global version 0.0.0}
%{!?srcversion:%global srcversion %{version}}

# Script-only package (Python); no native debuginfo.
%global debug_package %{nil}

Name:           iconlibutils
Version:        %{version}
Release:        1%{?dist}
Summary:        search and manage icons from installed icon libraries

License:        AGPL-3.0-or-later
URL:            https://github.com/lenik/iconlibutils
Packager:       Lenik <iconlibutils@bodz.net>
Source0:        %{name}-%{srcversion}.tar.xz
BuildArch:      noarch

BuildRequires:  meson
BuildRequires:  ninja-build
BuildRequires:  python3
BuildRequires:  python3-devel
BuildRequires:  python3-rpm-macros
BuildRequires:  gettext
BuildRequires:  asciidoctor

Requires:       python3
Requires:       python3-inflect
Requires:       python3-cairosvg
Requires:       wordnet-base
Suggests:       themestylebrowser
Suggests:       python3-faiss
Suggests:       python3-pillow

%description
iconlibutils provides the iconlib command to search, inspect, pull, and
browse icons from libraries such as tabler-icons, streamline-vectors, and
heroicons. findicon is a shortcut for iconlib search. Library discovery
uses drop-in metadata under %{_datadir}/iconlibutils/library/. Plain-English
search uses offline WordNet (wordnet-base) and python3-inflect; FAISS
indexes enrich results when present.

%prep
%setup -q -n %{name}-%{srcversion}

%build
meson setup build \
    --prefix=%{_prefix} \
    --bindir=%{_bindir} \
    --datadir=%{_datadir} \
    --mandir=%{_mandir} \
    --sysconfdir=%{_sysconfdir} \
    --localstatedir=%{_localstatedir} \
    --buildtype=plain
meson compile -C build

%install
meson install -C build --destdir=%{buildroot}

%files
%{_bindir}/iconlib
%{_bindir}/findicon
/usr/lib/python3*/site-packages/iconlib/
%{_datadir}/iconlibutils/
%{_datadir}/bash-completion/completions/iconlib
%{_datadir}/bash-completion/completions/findicon
%{_mandir}/man1/iconlib.1*
%{_mandir}/man1/findicon.1*
%{_mandir}/*/man1/iconlib.1*
%{_mandir}/*/man1/findicon.1*
%{_datadir}/doc/%{name}/
%{_datadir}/locale/*/LC_MESSAGES/iconlibutils.mo

%changelog
* Fri Sep 11 2026 Lenik <iconlibutils@bodz.net>
- Ship multi-command iconlib; require python3-pattern.
- Add findicon and shared Python modules to %%files.
- Mark noarch; align Summary with debian Description.

* Thu Aug 20 2026 Lenik <iconlibutils@bodz.net>
- Align spec with debian/control (Meson, AGPL-3.0-or-later).
- Version comes from `zfr version`, the same method meson.build uses.
