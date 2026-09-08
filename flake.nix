{
  inputs = {
    flake-parts.url = "github:hercules-ci/flake-parts";
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs = inputs@{ flake-parts, ... }:
    flake-parts.lib.mkFlake { inherit inputs; } {
      systems = [ "x86_64-linux" "aarch64-linux" "aarch64-darwin" ];
      perSystem = { config, pkgs, ... }: {
        packages.burn = pkgs.writeShellApplication (let
          python = pkgs.python3.withPackages (ps: [ ps.trio ]);
        in {
          name = "burn";
          text = ''
            exec ${python}/bin/python ${./burn.py} "$@"
          '';
        });
        packages.default = config.packages.burn;

        apps.burn = {
          type = "app";
          program = "${config.packages.burn}/bin/burn";
          meta.description = "burn after s/reading/writing";
        };
        apps.default = config.apps.burn;

        devShells.default = pkgs.mkShell {
          packages = [ pkgs.uv ];
        };
      };
    };
}
