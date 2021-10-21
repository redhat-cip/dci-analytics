Name:             dci-analytics
Version:          0.1.0
Release:          1.VERS%{?dist}
Summary:          DCI Analytics engine
License:          ASL 2.0
URL:              https://github.com/redhat-cip/%{name}
BuildArch:        noarch
Source0:          %{name}-%{version}.tar.gz

BuildRequires:    systemd

Requires:         podman

%description
The DCI analytics engine

%prep
%autosetup -n %{name}-%{version}

%build

%install
install -p -D -m 644 systemd/%{name}.service %{buildroot}%{_unitdir}/%{name}.service
install -p -D -m 644 systemd/%{name}-sync.service %{buildroot}%{_unitdir}/%{name}-sync.service
install -p -D -m 644 systemd/%{name}-sync.timer %{buildroot}%{_unitdir}/%{name}-sync.timer

%post
%systemd_post %{name}.service
%systemd_post %{name}-sync.service
%systemd_post %{name}-sync.timer

%preun
%systemd_preun %{name}.service
%systemd_preun %{name}-sync.service
%systemd_preun %{name}-sync.timer

%postun
%systemd_postun_with_restart %{name}.service
%systemd_postun_with_restart %{name}-sync.service
%systemd_postun_with_restart %{name}-sync.timer

%files
%{_unitdir}/*

%changelog
* Wed Oct 20 2021 Yassine Lamgarchal <ylamgarc@redhat.com> - 0.1.0-1
- Initial release
