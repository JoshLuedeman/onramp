import { Button, Avatar, Menu, MenuTrigger, MenuPopover, MenuList, MenuItem } from "@fluentui/react-components";
import { PersonRegular, SignOutRegular } from "@fluentui/react-icons";
import { useAuth } from "../../auth";

export default function AuthButton() {
  const { isAuthenticated, user, login, logout } = useAuth();

  if (!isAuthenticated) {
    return (
      <Button appearance="primary" icon={<PersonRegular />} onClick={login}>
        Sign In
      </Button>
    );
  }

  return (
    <Menu>
      <MenuTrigger disableButtonEnhancement>
        <Button appearance="subtle" icon={<Avatar name={user?.name} size={28} />}>
          {user?.name}
        </Button>
      </MenuTrigger>
      <MenuPopover>
        <MenuList>
          <MenuItem icon={<SignOutRegular />} onClick={logout}>
            Sign Out
          </MenuItem>
        </MenuList>
      </MenuPopover>
    </Menu>
  );
}
