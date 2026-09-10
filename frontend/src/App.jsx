import { useState } from "react";
import RoleSelection from "./components/RoleSelection";
import UserLogin from "./components/UserLogin";
import OfficerLogin from "./components/OfficerLogin";
import UserDashboard from "./components/UserDashboard";
import OfficerDashboard from "./components/OfficerDashboard";

export default function App() {
  const [page, setPage] = useState("roles");
  const [currentUser, setCurrentUser] = useState(null);

  const handleLogin = (user) => {
    setCurrentUser(user);
    setPage(
      user.role === "user"
        ? "userDashboard"
        : "officerDashboard"
    );
  };

  const handleLogout = () => {
    setCurrentUser(null);
    setPage("roles");
  };

  if (page === "roles") {
    return (
      <RoleSelection
        onSelectRole={(role) => setPage(`${role}Login`)}
      />
    );
  }

  if (page === "userLogin") {
    return (
      <UserLogin
        onLogin={handleLogin}
        onBack={() => setPage("roles")}
      />
    );
  }

  if (page === "officerLogin") {
    return (
      <OfficerLogin
        onLogin={handleLogin}
        onBack={() => setPage("roles")}
      />
    );
  }

  if (page === "userDashboard") {
    return (
      <UserDashboard
        user={currentUser}
        onLogout={handleLogout}
      />
    );
  }

  if (page === "officerDashboard") {
    return (
      <OfficerDashboard
        user={currentUser}
        onLogout={handleLogout}
      />
    );
  }

  return null;
}