import React from "react";
import NavBar from "../common/navBar";

const styles = {
  container: {
    padding: "24px",
    fontFamily: "sans-serif",
    maxWidth: "800px",
    margin: "auto",
  },
  title: { fontSize: "32px", fontWeight: "bold", marginBottom: "16px" },
  subtitle: { fontStyle: "italic", marginBottom: "24px" },
  sectionHeader: {
    fontSize: "18px",
    fontWeight: "bold",
    marginBottom: "8px",
    marginTop: "24px",
  },
  paragraph: { marginBottom: "16px", lineHeight: "1.6" },
  stepList: { marginBottom: "16px", lineHeight: "1.8", paddingLeft: "24px" },
};

export default function DataDeletionPolicy() {
  return (
    <div className="container mx-auto flex items-start mt-20 lg:mt-28">
      <NavBar />
      <div
        className="w-full h-[85vh] flex flex-col mx-3 lg:mx-0 border rounded-2xl bg-white 
               shadow p-5 overflow-y-scroll"
      >
        <div>
          <h1 style={styles.title}>Data Deletion Policy</h1>
          <p style={styles.subtitle}>Last Updated: July 16, 2026</p>

          <p style={styles.paragraph}>
            Cloutgrid, developed and operated by Cloutivity Private Limited,
            gives every user full control over their account and personal
            data. This page explains exactly how to request deletion of your
            Cloutgrid account, what happens when you do, and what data is
            affected. This policy applies to all users, including Creator
            Users and Business Users.
          </p>
        </div>

        <div>
          <h2 style={styles.sectionHeader}>How to Delete Your Account</h2>
          <p style={styles.paragraph}>
            You can permanently delete your Cloutgrid account directly from
            within the app. No email or manual request is required.
          </p>
          <ol style={styles.stepList}>
            <li>Open the Cloutgrid app and log in</li>
            <li>Go to Profile</li>
            <li>Tap Settings</li>
            <li>Tap Security</li>
            <li>Tap Delete Account and confirm</li>
          </ol>
          <p style={styles.paragraph}>
            If you no longer have the app installed, or are unable to access
            your account, you can instead request deletion by emailing us at{" "}
            <a href="mailto:info@cloutgrid.com">info@cloutgrid.com</a> from
            the email address associated with your account. We will process
            manual requests promptly after verifying your identity.
          </p>
        </div>

        <h2 style={styles.sectionHeader}>What Gets Deleted</h2>
        <p style={styles.paragraph}>
          Every feature and record in Cloutgrid is directly or indirectly
          linked to your user account. When your account is deleted, this
          link means the deletion cascades through our systems automatically,
          removing your account and all associated data in full, including:
        </p>
        <ol style={styles.stepList}>
          <li>Your profile information, including your name, email address, and profile photo</li>
          <li>All posts, media, and content you have uploaded</li>
          <li>Job postings, applications, and collaboration history</li>
          <li>Messages and conversations you are part of</li>
          <li>Comments you have made</li>
          <li>Any Instagram or YouTube account data stored by Cloutgrid, including access tokens and insights data retrieved through those integrations</li>
        </ol>
        <p style={styles.paragraph}>
          No trace of your account or associated content remains in our
          systems after deletion. We do not retain a copy of your data, and
          none of it can be recovered once deletion is complete.
        </p>

        <h2 style={styles.sectionHeader}>Instagram and YouTube Connections</h2>
        <p style={styles.paragraph}>
          If you connected an Instagram or YouTube account to Cloutgrid,
          deleting your Cloutgrid account permanently deletes our stored copy
          of any related data and access tokens. Please note that this
          removes Cloutgrid's access on our end, but does not itself revoke
          the connection from within your Instagram or YouTube account
          settings. If you would like to fully remove Cloutgrid's access from
          your Instagram or YouTube account directly, you can do so at any
          time through that platform's own connected-apps settings.
        </p>

        <h2 style={styles.sectionHeader}>When Deletion Takes Effect</h2>
        <p style={styles.paragraph}>
          Account deletion is instant. As soon as you confirm the deletion
          request in the app, or as soon as we process a manual request sent
          by email, your account and all associated data described above are
          permanently removed. This action cannot be undone, and we
          recommend downloading or saving any content you wish to keep before
          proceeding.
        </p>

        <h2 style={styles.sectionHeader}>Data Retention</h2>
        <p style={styles.paragraph}>
          Cloutgrid does not retain any personal data or user content after
          an account is deleted. There is no grace period, backup copy, or
          retention window. Once deletion is complete, your data is gone from
          our systems in full.
        </p>

        <h2 style={styles.sectionHeader}>Contact Us</h2>
        <p style={styles.paragraph}>
          Cloutivity Private Limited
          <br />
          Email: <a href="mailto:info@cloutgrid.com">info@cloutgrid.com</a>
          <br />
          <br />
          If you have any questions about this Data Deletion Policy or need
          help deleting your account, please reach out to us at the email
          address above.
        </p>
      </div>
    </div>
  );
}